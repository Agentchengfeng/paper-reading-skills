#!/usr/bin/env node
'use strict';

/*
 * paper-reading-skills installer
 *
 * Installs the paper-reading skill into ~/.claude/skills and links it into
 * ~/.codex/skills. No API keys, paper PDFs, generated HTML, or private notes
 * are included in this package.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const HOME = process.env.PAPER_READING_INSTALL_HOME || os.homedir();
const PKG_ROOT = path.resolve(__dirname, '..');
const PKG_SKILLS = path.join(PKG_ROOT, 'skills');
const CLAUDE_SKILLS = path.join(HOME, '.claude', 'skills');
const CODEX_SKILLS = path.join(HOME, '.codex', 'skills');
const SKILLS = ['paper-reading'];

const log = (s = '') => process.stdout.write(s + '\n');

function timestamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '-');
}

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else if (entry.isSymbolicLink()) {
      const target = fs.readlinkSync(s);
      try { fs.rmSync(d, { force: true, recursive: true }); } catch (_) {}
      fs.symlinkSync(target, d);
    } else {
      fs.copyFileSync(s, d);
      try { fs.chmodSync(d, fs.statSync(s).mode); } catch (_) {}
    }
  }
}

function backupAndRemove(target, label) {
  if (!fs.existsSync(target)) return null;
  const backupDir = path.join(CLAUDE_SKILLS, '.backups');
  fs.mkdirSync(backupDir, { recursive: true });
  const backup = path.join(backupDir, `${label}-${timestamp()}`);
  copyDir(target, backup);
  fs.rmSync(target, { recursive: true, force: true });
  return backup;
}

function installSkill(name) {
  const src = path.join(PKG_SKILLS, name);
  const dst = path.join(CLAUDE_SKILLS, name);
  if (!fs.existsSync(src)) throw new Error(`Missing packaged skill: ${src}`);
  let backup = null;
  if (fs.existsSync(dst)) {
    backup = backupAndRemove(dst, name);
  }
  copyDir(src, dst);
  for (const file of ['LICENSE', 'NOTICE.md', 'CITATION.cff']) {
    const packaged = path.join(PKG_ROOT, file);
    if (fs.existsSync(packaged)) fs.copyFileSync(packaged, path.join(dst, file));
  }
  log(`  ✓ ${name} -> ${dst}`);
  if (backup) log(`    backup: ${backup}`);
}

function linkCodexSkill(name) {
  fs.mkdirSync(CODEX_SKILLS, { recursive: true });
  const target = path.join(CLAUDE_SKILLS, name);
  const link = path.join(CODEX_SKILLS, name);

  if (fs.existsSync(link)) {
    const stat = fs.lstatSync(link);
    if (stat.isSymbolicLink()) {
      fs.rmSync(link, { force: true });
    } else {
      const backup = backupAndRemove(link, `${name}-codex`);
      if (backup) log(`    Codex backup: ${backup}`);
    }
  }

  fs.symlinkSync(target, link);
  log(`  ✓ ${name} linked -> ${link}`);
}

function doctor() {
  let ok = true;
  for (const name of SKILLS) {
    const claude = path.join(CLAUDE_SKILLS, name, 'SKILL.md');
    const notice = path.join(CLAUDE_SKILLS, name, 'NOTICE.md');
    const codex = path.join(CODEX_SKILLS, name);
    const exists = fs.existsSync(claude);
    const hasNotice = fs.existsSync(notice);
    const linked = fs.existsSync(codex) && fs.lstatSync(codex).isSymbolicLink();
    log(`${exists ? '✓' : '✗'} Claude skill: ${claude}`);
    log(`${hasNotice ? '✓' : '✗'} Attribution notice: ${notice}`);
    log(`${linked ? '✓' : '✗'} Codex symlink: ${codex}`);
    ok = ok && exists && hasNotice && linked;
  }
  try {
    execSync('python3 --version', { stdio: 'ignore' });
    log('✓ python3 available');
  } catch (_) {
    log('! python3 not found. The HTML annotation bridge needs python3.');
    ok = false;
  }
  process.exit(ok ? 0 : 1);
}

function uninstall() {
  for (const name of SKILLS) {
    const claude = path.join(CLAUDE_SKILLS, name);
    const codex = path.join(CODEX_SKILLS, name);
    if (fs.existsSync(codex)) fs.rmSync(codex, { recursive: true, force: true });
    if (fs.existsSync(claude)) {
      const backup = backupAndRemove(claude, `${name}-removed`);
      log(`  ✓ removed ${name}; backup: ${backup}`);
    }
  }
}

function printHelp() {
  log('paper-reading-skills');
  log('');
  log('Install the paper-reading Claude Code / Codex skill.');
  log('');
  log('Usage:');
  log('  npx -y github:Agentchengfeng/paper-reading-skills install');
  log('  npx -y github:Agentchengfeng/paper-reading-skills cpm install');
  log('  paper-reading-skills install');
  log('  paper-reading-cpm install');
  log('');
  log('Commands:');
  log('  install     Install/update ~/.claude/skills/paper-reading and link Codex');
  log('  doctor      Check installed files and python3');
  log('  uninstall   Remove installed skill after making a backup');
  log('  help        Show this help');
  log('');
  log('For tests only: set PAPER_READING_INSTALL_HOME=/tmp/some-home.');
}

function main() {
  let args = process.argv.slice(2);
  if (args[0] === 'cpm') args = args.slice(1);
  const cmd = args[0] || 'install';

  if (cmd === 'help' || cmd === '--help' || cmd === '-h') return printHelp();
  if (cmd === 'doctor') return doctor();
  if (cmd === 'uninstall') return uninstall();
  if (cmd !== 'install') {
    log(`Unknown command: ${cmd}`);
    printHelp();
    process.exit(1);
  }

  log('▶ Installing paper-reading-skills');
  fs.mkdirSync(CLAUDE_SKILLS, { recursive: true });
  for (const name of SKILLS) installSkill(name);
  for (const name of SKILLS) linkCodexSkill(name);

  try {
    execSync('python3 --version', { stdio: 'ignore' });
    log('  ✓ python3 available');
  } catch (_) {
    log('  ! python3 not found. Install python3 before using the annotation bridge.');
  }

  log('');
  log('Done. Open a new Claude Code / Codex session, then ask for paper-reading tasks.');
  log('Bridge script: ~/.claude/skills/paper-reading/scripts/bridge.py');
}

main();
