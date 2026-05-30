import fs from 'fs';
import path from 'path';

const root = path.resolve(process.cwd());
const sourceDir = path.join(root, 'frontend');
const outputDir = path.join(root, '.vercel_build_output', 'static');

function removeDir(targetPath) {
  fs.rmSync(targetPath, { recursive: true, force: true });
}

function ensureDir(targetPath) {
  fs.mkdirSync(targetPath, { recursive: true });
}

function copyRecursive(sourcePath, destinationPath) {
  const stats = fs.statSync(sourcePath);
  if (stats.isDirectory()) {
    ensureDir(destinationPath);
    for (const entry of fs.readdirSync(sourcePath)) {
      copyRecursive(path.join(sourcePath, entry), path.join(destinationPath, entry));
    }
    return;
  }

  ensureDir(path.dirname(destinationPath));
  fs.copyFileSync(sourcePath, destinationPath);
}

removeDir(path.join(root, '.vercel_build_output'));
ensureDir(outputDir);

for (const entry of fs.readdirSync(sourceDir)) {
  copyRecursive(path.join(sourceDir, entry), path.join(outputDir, entry));
}

console.log(`Copied static site from ${sourceDir} to ${outputDir}`);