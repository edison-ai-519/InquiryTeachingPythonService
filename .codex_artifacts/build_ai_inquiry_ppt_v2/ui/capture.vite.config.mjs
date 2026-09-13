// 仅用于截图的隔离配置；应用源码及其配置保持原样。
import original from '../../../frontend/vite.config.ts';
import { fileURLToPath } from 'node:url';
const localPath = (value) => fileURLToPath(new URL(value, import.meta.url));
export default {
  ...original,
  resolve: {
    ...original.resolve,
    alias: {
      ...original.resolve.alias,
      'lucide-vue-next': localPath('./lucide-dependency/package/dist/esm/lucide-vue-next.js'),
      'vue': localPath('../../../frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'),
    },
  },
  cacheDir: localPath('./vite-cache'),
  server: { host: '127.0.0.1', port: 5179, strictPort: true, fs: { allow: [localPath('../../../')] } },
};
