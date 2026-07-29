/**
 * Smoke agregado FRONTEND-DEPOSIT-POLICY-01.
 * Delegates para test:money e test:api-errors.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));

for (const script of ['verify-money.mjs', 'verify-api-errors.mjs']) {
  const r = spawnSync(process.execPath, [path.join(dir, script)], {
    stdio: 'inherit',
  });
  if (r.status !== 0) {
    process.exit(r.status ?? 1);
  }
}

console.log('verify-deposit-policy: OK');
