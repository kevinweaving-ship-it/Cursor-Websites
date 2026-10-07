#!/usr/bin/env php
<?php
/**
 * Create or update Dolibarr user `dash` with the existing GoWiFi dashboard
 * password. Authentication only — does not touch books or trial imports.
 *
 * Password source (first match):
 *   DASH_PASS env, /root/secrets/dash.env, /root/secrets/.dash-recovered
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "cli only\n");
	exit(1);
}

$pass = getenv('DASH_PASS') ?: '';
if ($pass === '' && is_readable('/root/secrets/dash.env')) {
	foreach (file('/root/secrets/dash.env', FILE_IGNORE_NEW_LINES) as $line) {
		if (str_starts_with($line, 'DASH_PASS=')) {
			$pass = substr($line, strlen('DASH_PASS='));
			$pass = trim($pass, " \t\"'");
		}
	}
}
if ($pass === '' && is_readable('/root/secrets/.dash-recovered')) {
	$pass = trim((string) file_get_contents('/root/secrets/.dash-recovered'));
}
if ($pass === '') {
	fwrite(STDERR, "missing DASH_PASS\n");
	exit(1);
}

$htpasswd = '/home/user-data/www/.gowifi-dash.htpasswd';
if (!is_readable($htpasswd)) {
	fwrite(STDERR, "missing htpasswd\n");
	exit(1);
}
$stored = trim((string) file_get_contents($htpasswd));
if (!preg_match('/^dash:(.+)$/', $stored, $m)) {
	fwrite(STDERR, "htpasswd user is not dash\n");
	exit(1);
}
if (!hash_equals($m[1], crypt($pass, $m[1]))) {
	fwrite(STDERR, "password does not match existing dashboard htpasswd\n");
	exit(1);
}

chdir('/opt/dolibarr/htdocs');
require 'master.inc.php';
require_once DOL_DOCUMENT_ROOT.'/user/class/user.class.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/security.lib.php';

$actor = new User($db);
if ($actor->fetch(1) <= 0) {
	fwrite(STDERR, "cannot fetch admin actor\n");
	exit(1);
}

$u = new User($db);
$exists = $u->fetch(0, 'dash');
if ($exists <= 0) {
	$u = new User($db);
	$u->login = 'dash';
	$u->lastname = 'Dashboard';
	$u->firstname = 'GoWiFi';
	$u->admin = 1;
	$u->entity = 1;
	$id = $u->create($actor, 1);
	if ($id <= 0) {
		fwrite(STDERR, 'create failed: '.$u->error."\n");
		exit(1);
	}
	if ($u->fetch($id) <= 0) {
		fwrite(STDERR, "fetch after create failed\n");
		exit(1);
	}
}

$u->admin = 1;
$u->lastname = $u->lastname ?: 'Dashboard';
$u->firstname = $u->firstname ?: 'GoWiFi';
if (property_exists($u, 'statut')) {
	$u->statut = 1;
}
if (property_exists($u, 'status')) {
	$u->status = 1;
}
$upd = $u->update($actor, 1);
if ($upd < 0) {
	fwrite(STDERR, 'update failed: '.$u->error."\n");
	exit(1);
}

// Existing dashboard password is shorter than Dolibarr's generator minimum.
// Hash it with Dolibarr's own function and store the hash so both prompts match.
$crypted = dol_hash($pass);
$set = $u->setPassword($actor, $crypted, 0, 1, 0, 1);
if (!is_string($set) || strlen($set) < 8) {
	fwrite(STDERR, 'setPassword failed: '.$u->error."\n");
	exit(1);
}

$u->fetch(0, 'dash');
$hash = $u->pass_indatabase_crypted ?: $u->pass_crypted;
if (!$hash || !dol_verifyHash($pass, $hash)) {
	fwrite(STDERR, "dolibarr hash verify failed\n");
	exit(1);
}

@umask(077);
$dashEnv = "DASH_USER=dash\nDASH_PASS=".$pass."\nDASH_URL=https://gowifi.co.za/dolibarr/\n";
if (file_put_contents('/root/secrets/dash.env', $dashEnv) === false) {
	fwrite(STDERR, "failed writing dash.env\n");
	exit(1);
}
chmod('/root/secrets/dash.env', 0600);

$envPath = '/root/secrets/dolibarr.env';
$env = is_readable($envPath) ? file_get_contents($envPath) : '';
$env = preg_replace('/^DOLIBARR_ADMIN=.*$/m', 'DOLIBARR_ADMIN=dash', $env);
$env = preg_replace('/^DOLIBARR_ADMIN_PASS=.*$/m', 'DOLIBARR_ADMIN_PASS='.$pass, $env);
if (strpos($env, 'DOLIBARR_ADMIN=') === false) {
	$env .= "DOLIBARR_ADMIN=dash\n";
}
if (strpos($env, 'DOLIBARR_ADMIN_PASS=') === false) {
	$env .= "DOLIBARR_ADMIN_PASS=".$pass."\n";
}
file_put_contents($envPath, $env);
chmod($envPath, 0600);

echo "dash_id=".$u->id." admin=".(int) $u->admin." pass_ok=yes htpasswd_ok=yes\n";
