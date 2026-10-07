#!/usr/bin/env php
<?php
/**
 * Enable Dolibarr modules that match the live GoWiFi dash.
 * Does not start billing cron or change imported invoices.
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "cli only\n");
	exit(1);
}

chdir('/opt/dolibarr/htdocs');
require 'master.inc.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/admin.lib.php';
require_once DOL_DOCUMENT_ROOT.'/categories/class/categorie.class.php';
require_once DOL_DOCUMENT_ROOT.'/societe/class/societe.class.php';

$actor = new User($db);
if ($actor->fetch('', 'dash') <= 0 && $actor->fetch(1) <= 0) {
	fwrite(STDERR, "cannot fetch user\n");
	exit(1);
}
$actor->getrights();

// Match how the box already works: clients, packages, monthly lines,
// Openserve cost, outages/UniFi faults, site visits, new-fibre quotes.
$modules = array(
	'modCategorie',
	'modProduct',
	'modService',
	'modContrat',
	'modTicket',
	'modFournisseur',
	'modMargin',
	'modNotification',
	'modFicheinter',
	'modPropale',
	'modCommande',
	'modCron',
	'modPrelevement',
	'modWebhook',
);

foreach ($modules as $mod) {
	$res = activateModule($mod);
	$errors = (is_array($res) && !empty($res['errors'])) ? json_encode($res['errors']) : '';
	echo ($errors ? "WARN $mod $errors\n" : "on $mod\n");
}

// Refresh dash user rights so the new menus appear.
$db->query("UPDATE ".$db->prefix()."user SET entity=0, admin=1, statut=1 WHERE login='dash'");
$db->query(
	"INSERT IGNORE INTO ".$db->prefix()."user_rights (entity, fk_user, fk_id)
	 SELECT 1, u.rowid, r.id FROM ".$db->prefix()."user u
	 JOIN ".$db->prefix()."rights_def r
	 WHERE u.login='dash'"
);

function ensure_category($db, $user, $label, $type)
{
	$cat = new Categorie($db);
	$found = $cat->fetch('', $label, $type);
	if ($found > 0) {
		return $cat->id;
	}
	$cat->label = $label;
	$cat->type = $type;
	$id = $cat->create($user);
	return $id > 0 ? $id : 0;
}

$wifi = ensure_category($db, $actor, 'WiFi', Categorie::TYPE_CUSTOMER);
$fibre = ensure_category($db, $actor, 'Fibre', Categorie::TYPE_CUSTOMER);
$pkg = ensure_category($db, $actor, 'Packages', Categorie::TYPE_PRODUCT);
$fault = ensure_category($db, $actor, 'Line fault', Categorie::TYPE_TICKET);

$sup = new Societe($db);
$sid = 0;
$sql = "SELECT rowid FROM ".$db->prefix()."societe WHERE nom='Openserve' AND entity=".(int) $conf->entity;
$res = $db->query($sql);
if ($res && ($obj = $db->fetch_object($res))) {
	$sid = (int) $obj->rowid;
} else {
	$sup->name = 'Openserve';
	$sup->nom = 'Openserve';
	$sup->client = 0;
	$sup->fournisseur = 1;
	$sup->country_id = 205;
	$sup->country_code = 'ZA';
	$sid = $sup->create($actor);
}

$tagged = 0;
$packFile = '/home/user-data/www/default/dash/accounts.json';
if (is_readable($packFile) && $wifi && $fibre) {
	$pack = json_decode((string) file_get_contents($packFile), true);
	$cards = ((isset($pack['clients']) && isset($pack['clients']['cards'])) ? $pack['clients']['cards'] : array());
	foreach ($cards as $card) {
		$name = isset($card['name']) ? $card['name'] : '';
		$access = isset($card['access']) ? $card['access'] : '';
		if ($name === '' || ($access !== 'fibre' && $access !== 'wireless' && $access !== 'wifi')) {
			continue;
		}
		$q = $db->query("SELECT rowid FROM ".$db->prefix()."societe WHERE nom='".$db->escape($name)."' AND entity=".(int) $conf->entity);
		$obj = $q ? $db->fetch_object($q) : null;
		if (!$obj) {
			continue;
		}
		$soc = new Societe($db);
		if ($soc->fetch((int) $obj->rowid) <= 0) {
			continue;
		}
		$cat = new Categorie($db);
		$cid = ($access === 'fibre') ? $fibre : $wifi;
		if ($cat->fetch($cid) > 0 && $cat->add_type($soc, 'customer') >= 0) {
			$tagged++;
		}
	}
}

echo "cats wifi=$wifi fibre=$fibre packages=$pkg fault=$fault openserve=$sid tagged=$tagged\n";
