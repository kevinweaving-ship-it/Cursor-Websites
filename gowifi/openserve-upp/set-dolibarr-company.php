#!/usr/bin/env php
<?php
/**
 * Fill Dolibarr company + FNB from the live GoWiFi letterhead.
 * Does not touch client invoices or payments.
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "cli only\n");
	exit(1);
}

chdir('/opt/dolibarr/htdocs');
require 'master.inc.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/admin.lib.php';
require_once DOL_DOCUMENT_ROOT.'/compta/bank/class/account.class.php';

$actor = new User($db);
if ($actor->fetch(1) <= 0) {
	fwrite(STDERR, "cannot fetch admin\n");
	exit(1);
}

$fields = array(
	'MAIN_INFO_SOCIETE_NOM' => 'GoWifi (Pty) Ltd',
	'MAIN_INFO_SOCIETE_ADDRESS' => '21 4th Avenue',
	'MAIN_INFO_SOCIETE_ZIP' => '7200',
	'MAIN_INFO_SOCIETE_TOWN' => 'Voelklip',
	'MAIN_INFO_SOCIETE_COUNTRY' => '205',
	'MAIN_INFO_SOCIETE_TEL' => '076 263 9937',
	'MAIN_INFO_SOCIETE_MAIL' => 'accounts@go-wifi.co.za',
	'MAIN_INFO_SOCIETE_MANAGERS' => 'Kevin Weaving',
	'MAIN_INFO_SOCIETE_FORME_JURIDIQUE' => '(Pty) Ltd',
	'MAIN_INFO_SIREN' => '2020/514776/07',
	'MAIN_INFO_TVAINTRA' => '',
	'MAIN_INFO_SOCIETE_NOTE' => 'Fibre and WiFi · Western Cape',
	'MAIN_INFO_SOCIETE_SETUP_TODO_WARNING' => '0',
);

foreach ($fields as $name => $value) {
	$ok = dolibarr_set_const($db, $name, $value, 'chaine', 0, '', $conf->entity);
	if ($ok < 0) {
		fwrite(STDERR, "const failed $name\n");
		exit(1);
	}
}

$acc = new Account($db);
$sql = "SELECT rowid FROM ".$db->prefix()."bank_account WHERE ref='FNB' AND entity=".(int) $conf->entity;
$res = $db->query($sql);
$obj = $res ? $db->fetch_object($res) : null;
if ($obj && $acc->fetch((int) $obj->rowid) > 0) {
	$acc->label = 'FNB current';
	$acc->bank = 'First National Bank';
	$acc->number = '62860060278';
	$acc->code_banque = '200412';
	$acc->domiciliation = 'Hermanus';
	$acc->proprio = 'GoWifi (Pty) Ltd';
	$acc->owner_address = '21 4th Avenue';
	$acc->owner_zip = '7200';
	$acc->owner_town = 'Voelklip';
	$acc->country_id = 205;
	$acc->fk_pays = 205;
	$acc->currency_code = 'ZAR';
	$upd = $acc->update($actor);
	if ($upd < 0) {
		fwrite(STDERR, 'bank update failed: '.$acc->error."\n");
		exit(1);
	}
}

$soc = (int) $db->query("SELECT COUNT(*) c FROM ".$db->prefix()."societe")->fetch_object()->c;
$fac = (int) $db->query("SELECT COUNT(*) c FROM ".$db->prefix()."facture")->fetch_object()->c;
echo "company=GoWifi (Pty) Ltd clients=$soc invoices=$fac bank=62860060278\n";
