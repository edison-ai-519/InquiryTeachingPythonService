from __future__ import annotations

import asyncio
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, TextIO
from urllib.parse import urlparse

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.core.config import Settings, get_settings
from app.db.models import (
    GlobiImportRunModel,
    GlobiImportInteractionModel,
    GlobiInteractionModel,
    KnowledgeEntityModel,
    KnowledgeEntityTaxonModel,
    KnowledgeRelationEvidenceModel,
    KnowledgeRelationGlobiEvidenceModel,
    KnowledgeRelationModel,
)


GLOBI_IMPORTER_VERSION = "globi-structured-v1"
ALLOWED_GLOBI_HOSTS = {
    "api.globalbioticinteractions.org",
    "depot.globalbioticinteractions.org",
    "globalbioticinteractions.org",
    "www.globalbioticinteractions.org",
    "zenodo.org",
    "download.zenodo.org",
}
DEFAULT_INTERACTION_TYPES = {
    "eats",
    "preyson",
    "eatenby",
    "preyeduponby",
    "pollinates",
    "pollinatedby",
    "visitsflowersof",
    "flowersvisitedby",
    "hashabitat",
    "parasiteof",
    "hasparasite",
}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _future_iso(seconds: int) -> str:
    return (
        dt.datetime.now(dt.timezone.utc).astimezone() + dt.timedelta(seconds=seconds)
    ).isoformat()


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def _compact(value: str) -> str:
    return re.sub(r"[^a-z]", "", (value or "").casefold())


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _field(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _common_names(value: str) -> list[str]:
    result = []
    for item in re.split(r"\s*\|\s*", value or ""):
        item = item.strip()
        if item and item not in result:
            result.append(item)
    return result


def _external_key(value: str) -> tuple[str, str]:
    token = re.split(r"\s*\|\s*", value or "")[0].strip()
    if not token:
        return "", ""
    if ":" in token:
        authority = token.split(":", 1)[0].strip().upper()
    else:
        authority = "GLOBI"
    return authority, token


@dataclass(frozen=True)
class GlobiImportOptions:
    include_insect_insect: bool = True
    keep_unknown_region: bool = True
    batch_size: int = 1000
    interaction_types: tuple[str, ...] = tuple(sorted(DEFAULT_INTERACTION_TYPES))

    @classmethod
    def from_dict(cls, payload: dict | None) -> "GlobiImportOptions":
        payload = payload or {}
        requested = payload.get("interaction_types") or DEFAULT_INTERACTION_TYPES
        normalized = tuple(
            sorted(
                {
                    _compact(str(item))
                    for item in requested
                    if _compact(str(item)) in DEFAULT_INTERACTION_TYPES
                }
            )
        )
        return cls(
            include_insect_insect=bool(payload.get("include_insect_insect", True)),
            keep_unknown_region=bool(payload.get("keep_unknown_region", True)),
            batch_size=max(100, min(int(payload.get("batch_size", 1000)), 10000)),
            interaction_types=normalized or tuple(sorted(DEFAULT_INTERACTION_TYPES)),
        )

    def as_dict(self) -> dict:
        return {
            "include_insect_insect": self.include_insect_insect,
            "keep_unknown_region": self.keep_unknown_region,
            "batch_size": self.batch_size,
            "interaction_types": list(self.interaction_types),
        }


@dataclass(frozen=True)
class TaxonCandidate:
    name: str
    entity_type: str
    external_id: str
    common_names: str
    path: str
    path_ids: str
    rank: str


@dataclass(frozen=True)
class NormalizedInteraction:
    subject: TaxonCandidate
    predicate: str
    object: TaxonCandidate
    raw_interaction_type: str
    study_source_id: str
    study_source_citation: str
    study_url: str
    study_doi: str
    study_source_archive_uri: str
    locality: str
    latitude: str
    longitude: str
    event_date: str
    source_last_seen_at: str
    region_status: str
    record_hash: str


class GlobiImportService:
    def __init__(self, db: Session):
        self.db = db
        self._entity_name_index: dict[tuple[str, str], set[str]] | None = None

    @staticmethod
    def validate_source_url(source_url: str) -> None:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or (parsed.hostname or "").casefold() not in ALLOWED_GLOBI_HOSTS:
            raise ValueError("GloBI 下载地址必须使用受信任的 HTTPS 官方域名")

    @staticmethod
    def checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @classmethod
    def download(cls, source_url: str) -> Path:
        cls.validate_source_url(source_url)
        suffix = Path(urlparse(source_url).path).suffix or ".csv"
        handle = tempfile.NamedTemporaryFile(prefix="globi-", suffix=suffix, delete=False)
        path = Path(handle.name)
        try:
            with handle, httpx.stream("GET", source_url, follow_redirects=True, timeout=120.0) as response:
                response.raise_for_status()
                final_host = (response.url.host or "").casefold()
                if response.url.scheme != "https" or final_host not in ALLOWED_GLOBI_HOSTS:
                    raise ValueError("GloBI 下载地址重定向到了非受信任域名")
                for block in response.iter_bytes(1024 * 1024):
                    handle.write(block)
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @contextmanager
    def _csv_reader(self, path: Path) -> Iterator[csv.DictReader]:
        binary = path.open("rb")
        nested: io.BufferedIOBase | gzip.GzipFile | None = None
        text_stream: TextIO | None = None
        archive: zipfile.ZipFile | None = None
        try:
            magic = binary.read(4)
            binary.seek(0)
            if magic[:2] == b"\x1f\x8b":
                nested = gzip.GzipFile(fileobj=binary)
            elif magic[:2] == b"PK":
                archive = zipfile.ZipFile(binary)
                members = [name for name in archive.namelist() if name.casefold().endswith((".csv", ".tsv"))]
                if not members:
                    raise ValueError("GloBI 压缩包中没有 CSV 或 TSV 文件")
                nested = archive.open(members[0])
            else:
                nested = binary
            text_stream = io.TextIOWrapper(nested, encoding="utf-8-sig", errors="replace", newline="")
            sample = text_stream.read(8192)
            text_stream.seek(0)
            delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
            reader = csv.DictReader(text_stream, delimiter=delimiter)
            if not reader.fieldnames:
                raise ValueError("GloBI 文件缺少表头")
            reader.fieldnames = [str(name or "").strip() for name in reader.fieldnames]
            yield reader
        finally:
            if text_stream is not None:
                text_stream.close()
            elif nested is not None and nested is not binary:
                nested.close()
            if archive is not None:
                archive.close()
            if not binary.closed:
                binary.close()

    def preview(self, path: Path, options: GlobiImportOptions) -> dict:
        stats = self._empty_stats()
        seen_hashes: set[str] = set()
        with self._csv_reader(path) as reader:
            for row in reader:
                stats["total_rows"] += 1
                item, reason, candidate = self.normalize_row(row, options)
                if candidate:
                    stats["candidate_rows"] += 1
                if item is None:
                    self._reject(stats, reason, row)
                    continue
                if item.record_hash in seen_hashes:
                    self._reject(stats, "duplicate_record", row)
                    continue
                seen_hashes.add(item.record_hash)
                stats["accepted_rows"] += 1
                stats["predicate_counts"][item.predicate] = stats["predicate_counts"].get(item.predicate, 0) + 1
        return stats

    def create_run(
        self,
        *,
        version: str,
        source_url: str,
        source_name: str,
        staged_path: str,
        options: GlobiImportOptions,
        created_by: str,
        delete_staged_after: bool = False,
    ) -> dict:
        if not staged_path and not source_url:
            raise ValueError("必须上传 GloBI CSV/TSV 文件或提供官方下载地址")
        if source_url:
            self.validate_source_url(source_url)
        timestamp = _now_iso()
        run = GlobiImportRunModel(
            id=f"globi_run_{uuid.uuid4().hex}",
            version=version.strip() or "unspecified",
            source_url=source_url.strip(),
            source_name=source_name.strip() or Path(staged_path).name or "GloBI",
            filter_json=_json(
                {
                    **options.as_dict(),
                    "staged_path": staged_path,
                    "delete_staged_after": delete_staged_after,
                }
            ),
            status="queued",
            created_by=created_by,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.db.add(run)
        self.db.flush()
        return self.serialize_run(run)

    @classmethod
    def process_run_background(cls, run_id: str, claimed: bool = False) -> None:
        db = SessionLocal()
        try:
            try:
                cls(db).process_run(run_id, claimed=claimed)
            except Exception:
                # process_run persists the failure details for the polling API.
                pass
        finally:
            db.close()

    def process_run(self, run_id: str, *, claimed: bool = False) -> dict:
        run = self.db.get(GlobiImportRunModel, run_id)
        if run is None:
            raise LookupError("GloBI 导入任务不存在")
        if claimed and run.status != "running":
            return self.serialize_run(run)
        if not claimed and run.status not in {"queued", "failed"}:
            return self.serialize_run(run)
        try:
            filters = json.loads(run.filter_json or "{}")
        except json.JSONDecodeError:
            filters = {}
        options = GlobiImportOptions.from_dict(filters)
        staged_path = str(filters.get("staged_path") or "")
        delete_staged_after = bool(filters.get("delete_staged_after", False))
        downloaded = False
        completed = False
        path = Path(staged_path) if staged_path else None
        timestamp = _now_iso()
        if not claimed:
            run.status = "running"
            run.attempts = int(run.attempts or 0) + 1
            run.started_at = run.started_at or timestamp
            run.lease_until = _future_iso(900)
            run.finished_at = ""
            run.last_error = ""
            run.updated_at = timestamp
            self.db.commit()
        try:
            if path is None:
                path = self.download(run.source_url)
                downloaded = True
            if not path.exists():
                raise ValueError("GloBI 导入文件不存在")
            run = self.db.get(GlobiImportRunModel, run_id)
            run.checksum = self.checksum(path)
            stats = self._import_path(run, path, options)
            self._apply_stats(run, stats)
            run.status = "completed"
            run.lease_until = ""
            run.finished_at = _now_iso()
            run.updated_at = run.finished_at
            self.db.commit()
            completed = True
            return self.serialize_run(run)
        except Exception as exc:
            self.db.rollback()
            run = self.db.get(GlobiImportRunModel, run_id)
            if run is not None:
                run.status = "failed"
                run.lease_until = ""
                run.last_error = f"{type(exc).__name__}: {exc}"
                run.finished_at = _now_iso()
                run.updated_at = run.finished_at
                self.db.commit()
            raise
        finally:
            if path is not None and (downloaded or (completed and delete_staged_after)):
                path.unlink(missing_ok=True)

    def _import_path(
        self,
        run: GlobiImportRunModel,
        path: Path,
        options: GlobiImportOptions,
    ) -> dict:
        stats = self._empty_stats()
        created_entities: set[str] = set()
        reused_entities: set[str] = set()
        created_relations: set[str] = set()
        updated_relations: set[str] = set()
        seen_hashes: set[str] = set()
        timestamp = _now_iso()
        with self._csv_reader(path) as reader:
            for row_index, row in enumerate(reader, start=1):
                stats["total_rows"] += 1
                item, reason, candidate = self.normalize_row(row, options)
                if candidate:
                    stats["candidate_rows"] += 1
                if item is None:
                    self._reject(stats, reason, row)
                    continue
                if item.record_hash in seen_hashes:
                    self._reject(stats, "duplicate_record", row)
                    continue
                seen_hashes.add(item.record_hash)
                existing_interaction = (
                    self.db.query(GlobiInteractionModel)
                    .filter(GlobiInteractionModel.record_hash == item.record_hash)
                    .first()
                )
                if existing_interaction is not None:
                    if self.db.get(
                        GlobiImportInteractionModel,
                        {"import_run_id": run.id, "interaction_id": existing_interaction.id},
                    ) is None:
                        self.db.add(
                            GlobiImportInteractionModel(
                                import_run_id=run.id,
                                interaction_id=existing_interaction.id,
                                created_at=timestamp,
                            )
                        )
                    stats["accepted_rows"] += 1
                    stats["duplicate_rows"] += 1
                    continue
                subject, subject_created = self._resolve_entity(item.subject, run)
                obj, object_created = self._resolve_entity(item.object, run)
                (created_entities if subject_created else reused_entities).add(subject.id)
                (created_entities if object_created else reused_entities).add(obj.id)
                relation, relation_created = self._resolve_relation(
                    subject,
                    item.predicate,
                    obj,
                    run,
                    timestamp,
                )
                (created_relations if relation_created else updated_relations).add(relation.id)
                interaction = self._create_interaction(run, item, subject.id, obj.id, timestamp)
                self.db.add(
                    GlobiImportInteractionModel(
                        import_run_id=run.id,
                        interaction_id=interaction.id,
                        created_at=timestamp,
                    )
                )
                self.db.add(
                    KnowledgeRelationGlobiEvidenceModel(
                        relation_id=relation.id,
                        interaction_id=interaction.id,
                        created_at=timestamp,
                    )
                )
                stats["accepted_rows"] += 1
                stats["predicate_counts"][item.predicate] = stats["predicate_counts"].get(item.predicate, 0) + 1
                if row_index % options.batch_size == 0:
                    self.db.flush()
        stats["created_entities"] = len(created_entities)
        stats["updated_entities"] = len(reused_entities - created_entities)
        stats["created_relations"] = len(created_relations)
        stats["updated_relations"] = len(updated_relations - created_relations)
        self.db.flush()
        return stats

    def normalize_row(
        self,
        row: dict[str, str],
        options: GlobiImportOptions,
    ) -> tuple[NormalizedInteraction | None, str, bool]:
        source = self._taxon(row, "source")
        target = self._taxon(row, "target")
        raw_type = _field(
            row,
            "interactionTypeName",
            "interaction_type",
            "interactionType",
            "interaction_type_name",
        )
        compact_type = _compact(raw_type)
        if source.entity_type not in {"insect", "plant"} or target.entity_type not in {"insect", "plant"}:
            return None, "unsupported_taxa", False
        if not (
            {source.entity_type, target.entity_type} == {"insect", "plant"}
            or source.entity_type == target.entity_type == "insect"
        ):
            return None, "unsupported_taxa", False
        if source.entity_type == target.entity_type == "insect" and not options.include_insect_insect:
            return None, "insect_insect_disabled", False
        if compact_type not in set(options.interaction_types):
            return None, "unsupported_interaction", False
        if not source.name or not target.name:
            return None, "missing_name", True
        if not source.external_id or not target.external_id:
            return None, "missing_external_id", True
        normalized = self._normalize_direction(source, compact_type, target)
        if normalized is None:
            return None, "unsupported_direction", True
        subject, predicate, obj = normalized
        if subject.external_id == obj.external_id:
            return None, "self_relation", True
        locality = _field(row, "localityName", "locality")
        latitude = _field(row, "latitude", "decimalLatitude")
        longitude = _field(row, "longitude", "decimalLongitude")
        region_status = "located" if locality or latitude or longitude else "global"
        if region_status == "global" and not options.keep_unknown_region:
            return None, "missing_region", True
        study_source_id = _field(
            row,
            "namespace",
            "study_external_id",
            "study_source_id",
            "studySourceId",
        )
        reference_citation = _field(
            row,
            "referenceCitation",
            "study_source_citation",
            "studySourceCitation",
            "study_citation",
            "studyCitation",
        )
        dataset_citation = _field(row, "citation")
        study_source_citation = " | ".join(
            dict.fromkeys(value for value in (reference_citation, dataset_citation) if value)
        )
        study_url = _field(row, "referenceUrl", "study_url", "studyUrl")
        study_doi = _field(row, "referenceDoi", "study_doi", "studyDoi")
        archive_uri = _field(
            row,
            "archiveURI",
            "sourceArchiveURI",
            "study_source_archive_uri",
            "studySourceArchiveURI",
        )
        source_last_seen_at = _field(
            row,
            "lastSeenAt",
            "study_source_last_seen_at",
            "studySourceLastSeenAt",
        )
        provenance = {
            "subject": subject.external_id,
            "predicate": predicate,
            "object": obj.external_id,
            "raw_type": raw_type,
            "study_source_id": study_source_id,
            "study_source_citation": study_source_citation,
            "study_url": study_url,
            "study_doi": study_doi,
            "study_source_archive_uri": archive_uri,
            "event_date": _field(
                row,
                "observationDateTime",
                "event_date",
                "eventDate",
                "http://rs.tdwg.org/dwc/terms/eventDate",
            ),
            "locality": locality,
            "latitude": latitude,
            "longitude": longitude,
            "source_last_seen_at": source_last_seen_at,
        }
        record_hash = hashlib.sha256(_json(provenance).encode("utf-8")).hexdigest()
        return NormalizedInteraction(
            subject=subject,
            predicate=predicate,
            object=obj,
            raw_interaction_type=raw_type,
            study_source_id=provenance["study_source_id"],
            study_source_citation=study_source_citation,
            study_url=provenance["study_url"],
            study_doi=provenance["study_doi"],
            study_source_archive_uri=archive_uri,
            locality=locality,
            latitude=latitude,
            longitude=longitude,
            event_date=provenance["event_date"],
            source_last_seen_at=source_last_seen_at,
            region_status=region_status,
            record_hash=record_hash,
        ), "", True

    @staticmethod
    def _normalize_direction(
        source: TaxonCandidate,
        interaction_type: str,
        target: TaxonCandidate,
    ) -> tuple[TaxonCandidate, str, TaxonCandidate] | None:
        inverse = interaction_type in {"eatenby", "preyeduponby", "pollinatedby", "flowersvisitedby", "hasparasite"}
        subject, obj = (target, source) if inverse else (source, target)
        if interaction_type in {"pollinates", "pollinatedby"}:
            predicate = "pollinates"
        elif interaction_type in {"visitsflowersof", "flowersvisitedby"}:
            predicate = "visits"
        elif interaction_type == "hashabitat":
            predicate = "lives_on"
        elif interaction_type in {"parasiteof", "hasparasite"}:
            predicate = "parasite_of"
        elif interaction_type in {"eats", "eatenby", "preyson", "preyeduponby"}:
            predicate = "feeds_on" if obj.entity_type == "plant" else "predator_of"
        else:
            return None
        if subject.entity_type != "insect":
            return None
        if predicate in {"feeds_on", "pollinates", "visits", "lives_on"} and obj.entity_type != "plant":
            return None
        if predicate in {"predator_of", "parasite_of"} and obj.entity_type != "insect":
            return None
        return subject, predicate, obj

    @staticmethod
    def _taxon(row: dict[str, str], side: str) -> TaxonCandidate:
        camel = "source" if side == "source" else "target"
        title = "Source" if side == "source" else "Target"
        name = _field(row, f"{side}_taxon_name", f"{camel}TaxonName")
        external_id = _field(row, f"{side}_taxon_external_id", f"{camel}TaxonId", f"{camel}TaxonExternalId")
        path = _field(row, f"{side}_taxon_path", f"{camel}TaxonPath")
        path_ids = _field(row, f"{side}_taxon_path_ids", f"{camel}TaxonPathIds")
        common_names = _field(row, f"{side}_taxon_common_names", f"{camel}TaxonCommonNames")
        rank = _field(row, f"{side}_taxon_rank", f"{camel}TaxonRank")
        class_name = _field(row, f"{side}_taxon_class_name", f"{camel}TaxonClassName")
        kingdom_name = _field(row, f"{side}_taxon_kingdom_name", f"{camel}TaxonKingdomName")
        path_tokens = {
            _normalized(token)
            for token in re.split(r"\s*\|\s*", path or "")
            if _normalized(token)
        }
        if _normalized(class_name) == "insecta" or "insecta" in path_tokens:
            entity_type = "insect"
        elif _normalized(kingdom_name) in {"plantae", "viridiplantae"} or path_tokens.intersection(
            {"plantae", "viridiplantae"}
        ):
            entity_type = "plant"
        else:
            entity_type = ""
        return TaxonCandidate(name, entity_type, external_id, common_names, path, path_ids, rank)

    def _resolve_entity(
        self,
        taxon: TaxonCandidate,
        run: GlobiImportRunModel,
    ) -> tuple[KnowledgeEntityModel, bool]:
        authority, external_id = _external_key(taxon.external_id)
        mapping = self.db.get(
            KnowledgeEntityTaxonModel,
            {"authority": authority, "external_id": external_id},
        )
        timestamp = _now_iso()
        if mapping is not None:
            entity = self.db.get(KnowledgeEntityModel, mapping.entity_id)
            if entity is None:
                raise ValueError("分类标识引用了不存在的图谱实体")
            mapping.scientific_name = taxon.name
            mapping.verbatim_name = taxon.name
            mapping.taxon_rank = taxon.rank
            mapping.taxon_path = taxon.path
            mapping.taxon_path_ids = taxon.path_ids
            mapping.common_names_json = _json(_common_names(taxon.common_names))
            mapping.updated_at = timestamp
            self._entity_ids_for_name(taxon.entity_type, _normalized(taxon.name)).add(entity.id)
            return entity, False
        normalized_name = _normalized(taxon.name)
        entity_ids = self._entity_ids_for_name(taxon.entity_type, normalized_name)
        matches = [self.db.get(KnowledgeEntityModel, entity_id) for entity_id in entity_ids]
        matches = [entity for entity in matches if entity is not None]
        created = not matches
        if len(matches) > 1:
            raise ValueError(f"学名“{taxon.name}”匹配到多个节点，需先人工归一")
        if matches:
            entity = matches[0]
            match_method = "scientific_name"
        else:
            entity = KnowledgeEntityModel(
                id=f"entity_globi_{hashlib.sha256(f'{authority}:{external_id}'.encode()).hexdigest()[:16]}",
                name=taxon.name,
                entity_type=taxon.entity_type,
                aliases_json="[]",
                description="",
                source=f"globi:{run.version}",
                origin="globi",
                management_mode="auto",
                extractor_model="GloBI",
                extractor_version=run.version,
                last_auto_sync_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self.db.add(entity)
            self.db.flush()
            match_method = "created"
        self.db.add(
            KnowledgeEntityTaxonModel(
                authority=authority,
                external_id=external_id,
                entity_id=entity.id,
                scientific_name=taxon.name,
                verbatim_name=taxon.name,
                taxon_rank=taxon.rank,
                taxon_path=taxon.path,
                taxon_path_ids=taxon.path_ids,
                common_names_json=_json(_common_names(taxon.common_names)),
                match_method=match_method,
                match_confidence="high",
                created_by_run_id=run.id,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        self.db.flush()
        self._entity_ids_for_name(taxon.entity_type, normalized_name).add(entity.id)
        return entity, created

    def _entity_ids_for_name(self, entity_type: str, normalized_name: str) -> set[str]:
        if self._entity_name_index is None:
            index: dict[tuple[str, str], set[str]] = {}
            entities = self.db.query(KnowledgeEntityModel).all()
            entity_types = {entity.id: entity.entity_type for entity in entities}
            for entity in entities:
                try:
                    aliases = json.loads(entity.aliases_json or "[]")
                except json.JSONDecodeError:
                    aliases = []
                for value in [entity.name, *aliases]:
                    key = (entity.entity_type, _normalized(str(value)))
                    if key[1]:
                        index.setdefault(key, set()).add(entity.id)
            for mapping in self.db.query(KnowledgeEntityTaxonModel).all():
                entity_type_value = entity_types.get(mapping.entity_id, "")
                for value in (mapping.scientific_name, mapping.verbatim_name):
                    key = (entity_type_value, _normalized(value))
                    if key[0] and key[1]:
                        index.setdefault(key, set()).add(mapping.entity_id)
            self._entity_name_index = index
        return self._entity_name_index.setdefault((entity_type, normalized_name), set())

    def _resolve_relation(
        self,
        subject: KnowledgeEntityModel,
        predicate: str,
        obj: KnowledgeEntityModel,
        run: GlobiImportRunModel,
        timestamp: str,
    ) -> tuple[KnowledgeRelationModel, bool]:
        relation = (
            self.db.query(KnowledgeRelationModel)
            .filter(
                KnowledgeRelationModel.subject_entity_id == subject.id,
                KnowledgeRelationModel.predicate == predicate,
                KnowledgeRelationModel.object_entity_id == obj.id,
            )
            .first()
        )
        created = relation is None
        source_label = f"GloBI {run.version}"
        if relation is None:
            relation = KnowledgeRelationModel(
                id=f"relation_globi_{hashlib.sha256(f'{subject.id}:{predicate}:{obj.id}'.encode()).hexdigest()[:16]}",
                subject_entity_id=subject.id,
                predicate=predicate,
                object_entity_id=obj.id,
                description=f"GloBI 全球数据库记录：{subject.name}与{obj.name}存在该生态关系；不能据此单独证明特定本地场景存在同样关系。",
                evidence_source=source_label,
                confidence="medium",
                origin="globi",
                management_mode="auto",
                status="active",
                extractor_model="GloBI",
                extractor_version=run.version,
                last_auto_sync_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self.db.add(relation)
            self.db.flush()
        elif relation.management_mode == "auto" and relation.status != "suppressed":
            relation.last_auto_sync_at = timestamp
            relation.updated_at = timestamp
            if relation.origin == "globi":
                relation.extractor_version = run.version
            if source_label not in (relation.evidence_source or ""):
                relation.evidence_source = "、".join(filter(None, [relation.evidence_source, source_label]))
        return relation, created

    def _create_interaction(
        self,
        run: GlobiImportRunModel,
        item: NormalizedInteraction,
        source_entity_id: str,
        target_entity_id: str,
        timestamp: str,
    ) -> GlobiInteractionModel:
        interaction = GlobiInteractionModel(
            id=f"globi_interaction_{item.record_hash[:24]}",
            import_run_id=run.id,
            source_taxon_external_id=item.subject.external_id,
            target_taxon_external_id=item.object.external_id,
            source_taxon_name=item.subject.name,
            target_taxon_name=item.object.name,
            source_taxon_common_names=item.subject.common_names,
            target_taxon_common_names=item.object.common_names,
            source_taxon_path=item.subject.path,
            target_taxon_path=item.object.path,
            raw_interaction_type=item.raw_interaction_type,
            normalized_predicate=item.predicate,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            study_source_id=item.study_source_id,
            study_source_citation=item.study_source_citation,
            study_url=item.study_url,
            study_doi=item.study_doi,
            study_source_archive_uri=item.study_source_archive_uri,
            locality=item.locality,
            latitude=item.latitude,
            longitude=item.longitude,
            event_date=item.event_date,
            source_last_seen_at=item.source_last_seen_at,
            region_status=item.region_status,
            record_hash=item.record_hash,
            created_at=timestamp,
        )
        self.db.add(interaction)
        self.db.flush()
        return interaction

    def list_runs(self, limit: int = 50) -> list[dict]:
        rows = (
            self.db.query(GlobiImportRunModel)
            .order_by(GlobiImportRunModel.created_at.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        return [self.serialize_run(row) for row in rows]

    def summary(self, run_id: str) -> dict:
        run = self.db.get(GlobiImportRunModel, run_id)
        if run is None:
            raise LookupError("GloBI 导入任务不存在")
        return self.serialize_run(run)

    def retry(self, run_id: str) -> dict:
        run = self.db.get(GlobiImportRunModel, run_id)
        if run is None:
            raise LookupError("GloBI 导入任务不存在")
        if run.status != "failed":
            raise ValueError("只有失败的 GloBI 导入任务可以重试")
        filters = self._parse_stats(run.filter_json)
        staged_path = str(filters.get("staged_path") or "")
        if not run.source_url and (not staged_path or not Path(staged_path).exists()):
            raise ValueError("原上传文件已不存在，请重新创建导入任务")
        run.status = "queued"
        run.lease_until = ""
        run.finished_at = ""
        run.last_error = ""
        run.updated_at = _now_iso()
        self.db.flush()
        return self.serialize_run(run)

    def rollback(self, run_id: str) -> dict:
        run = self.db.get(GlobiImportRunModel, run_id)
        if run is None:
            raise LookupError("GloBI 导入任务不存在")
        if run.status == "rolled_back":
            return self.serialize_run(run)
        if run.status != "completed":
            raise ValueError("只有已完成的 GloBI 导入任务可以回滚")
        associations = self.db.query(GlobiImportInteractionModel).filter(
            GlobiImportInteractionModel.import_run_id == run.id
        ).all()
        interaction_ids = [row.interaction_id for row in associations]
        interactions = (
            self.db.query(GlobiInteractionModel)
            .filter(GlobiInteractionModel.id.in_(interaction_ids))
            .all()
            if interaction_ids
            else []
        )
        entity_ids = {
            entity_id
            for row in interactions
            for entity_id in (row.source_entity_id, row.target_entity_id)
        }
        relation_ids = {
            row.relation_id
            for row in self.db.query(KnowledgeRelationGlobiEvidenceModel).filter(
                KnowledgeRelationGlobiEvidenceModel.interaction_id.in_(interaction_ids)
            ).all()
        } if interaction_ids else set()
        removable_interaction_ids: list[str] = []
        if interaction_ids:
            self.db.query(GlobiImportInteractionModel).filter(
                GlobiImportInteractionModel.import_run_id == run.id
            ).delete(synchronize_session=False)
            self.db.flush()
            for interaction_id in interaction_ids:
                still_referenced = self.db.query(GlobiImportInteractionModel.interaction_id).filter(
                    GlobiImportInteractionModel.interaction_id == interaction_id
                ).first()
                if not still_referenced:
                    removable_interaction_ids.append(interaction_id)
        if removable_interaction_ids:
            self.db.query(KnowledgeRelationGlobiEvidenceModel).filter(
                KnowledgeRelationGlobiEvidenceModel.interaction_id.in_(removable_interaction_ids)
            ).delete(synchronize_session=False)
            self.db.query(GlobiInteractionModel).filter(
                GlobiInteractionModel.id.in_(removable_interaction_ids)
            ).delete(synchronize_session=False)
        self.db.flush()
        removed_relations = 0
        for relation_id in relation_ids:
            relation = self.db.get(KnowledgeRelationModel, relation_id)
            if relation is None:
                continue
            has_external = self.db.query(KnowledgeRelationGlobiEvidenceModel.relation_id).filter(
                KnowledgeRelationGlobiEvidenceModel.relation_id == relation_id
            ).first()
            has_local = self.db.query(KnowledgeRelationEvidenceModel.relation_id).filter(
                KnowledgeRelationEvidenceModel.relation_id == relation_id
            ).first()
            if not has_external and not has_local and relation.origin == "globi" and relation.management_mode == "auto":
                self.db.delete(relation)
                removed_relations += 1
        self.db.flush()
        removed_entities = 0
        for entity_id in entity_ids:
            entity = self.db.get(KnowledgeEntityModel, entity_id)
            if entity is None or entity.origin != "globi" or entity.management_mode != "auto":
                continue
            has_relation = self.db.query(KnowledgeRelationModel.id).filter(
                or_(
                    KnowledgeRelationModel.subject_entity_id == entity_id,
                    KnowledgeRelationModel.object_entity_id == entity_id,
                )
            ).first()
            if not has_relation:
                self.db.delete(entity)
                removed_entities += 1
        run.status = "rolled_back"
        run.finished_at = _now_iso()
        run.updated_at = run.finished_at
        stats = self._parse_stats(run.stats_json)
        stats["rollback"] = {
            "interactions": len(removable_interaction_ids),
            "relations": removed_relations,
            "entities": removed_entities,
        }
        run.stats_json = _json(stats)
        self.db.flush()
        return self.serialize_run(run)

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "total_rows": 0,
            "candidate_rows": 0,
            "accepted_rows": 0,
            "rejected_rows": 0,
            "duplicate_rows": 0,
            "created_entities": 0,
            "updated_entities": 0,
            "created_relations": 0,
            "updated_relations": 0,
            "rejection_reasons": {},
            "rejection_samples": [],
            "predicate_counts": {},
        }

    @staticmethod
    def _reject(stats: dict, reason: str, row: dict[str, str]) -> None:
        stats["rejected_rows"] += 1
        stats["rejection_reasons"][reason] = stats["rejection_reasons"].get(reason, 0) + 1
        if len(stats["rejection_samples"]) < 20:
            stats["rejection_samples"].append(
                {
                    "reason": reason,
                    "source": _field(row, "source_taxon_name", "sourceTaxonName"),
                    "interaction": _field(
                        row,
                        "interactionTypeName",
                        "interaction_type",
                        "interactionType",
                    ),
                    "target": _field(row, "target_taxon_name", "targetTaxonName"),
                }
            )

    @staticmethod
    def _apply_stats(run: GlobiImportRunModel, stats: dict) -> None:
        for field in (
            "total_rows",
            "candidate_rows",
            "accepted_rows",
            "rejected_rows",
            "created_entities",
            "updated_entities",
            "created_relations",
            "updated_relations",
        ):
            setattr(run, field, int(stats.get(field, 0)))
        run.stats_json = _json(stats)

    @staticmethod
    def _parse_stats(raw: str) -> dict:
        try:
            value = json.loads(raw or "{}")
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    @classmethod
    def serialize_run(cls, run: GlobiImportRunModel) -> dict:
        try:
            filters = json.loads(run.filter_json or "{}")
        except json.JSONDecodeError:
            filters = {}
        filters.pop("staged_path", None)
        filters.pop("delete_staged_after", None)
        return {
            "id": run.id,
            "version": run.version,
            "source_url": run.source_url,
            "source_name": run.source_name,
            "checksum": run.checksum,
            "filters": filters,
            "status": run.status,
            "attempts": run.attempts,
            "total_rows": run.total_rows,
            "candidate_rows": run.candidate_rows,
            "accepted_rows": run.accepted_rows,
            "rejected_rows": run.rejected_rows,
            "created_entities": run.created_entities,
            "updated_entities": run.updated_entities,
            "created_relations": run.created_relations,
            "updated_relations": run.updated_relations,
            "stats": cls._parse_stats(run.stats_json),
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "last_error": run.last_error,
            "created_by": run.created_by,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }


class GlobiImportWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        if not self.settings.globi_import_worker_enabled:
            return
        while not self._stopped.is_set():
            run_id = self._claim_next_run()
            if run_id:
                await asyncio.to_thread(
                    GlobiImportService.process_run_background,
                    run_id,
                    True,
                )
                continue
            try:
                await asyncio.wait_for(
                    self._stopped.wait(),
                    timeout=self.settings.globi_import_worker_poll_seconds,
                )
            except asyncio.TimeoutError:
                pass

    @staticmethod
    def _claim_next_run() -> str:
        db = SessionLocal()
        try:
            now = _now_iso()
            available = or_(
                GlobiImportRunModel.status == "queued",
                (
                    (GlobiImportRunModel.status == "running")
                    & (GlobiImportRunModel.lease_until < now)
                ),
            )
            candidate = (
                db.query(GlobiImportRunModel)
                .filter(available)
                .order_by(GlobiImportRunModel.created_at.asc())
                .first()
            )
            if candidate is None:
                return ""
            run_id = candidate.id
            claimed = (
                db.query(GlobiImportRunModel)
                .filter(GlobiImportRunModel.id == run_id, available)
                .update(
                    {
                        GlobiImportRunModel.status: "running",
                        GlobiImportRunModel.attempts: GlobiImportRunModel.attempts + 1,
                        GlobiImportRunModel.started_at: candidate.started_at or now,
                        GlobiImportRunModel.finished_at: "",
                        GlobiImportRunModel.last_error: "",
                        GlobiImportRunModel.lease_until: _future_iso(900),
                        GlobiImportRunModel.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if claimed != 1:
                db.rollback()
                return ""
            db.commit()
            return run_id
        finally:
            db.close()

    def stop(self) -> None:
        self._stopped.set()
