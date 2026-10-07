#!/usr/bin/env php
<?php
/**
 * Prepare the later client portal: each customer will see only their
 * invoices, tickets, contracts and service jobs.
 * Does not create client logins or start public anonymous tickets.
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "cli only\n");
	exit(1);
}

chdir('/opt/dolibarr/htdocs');
require 'master.inc.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/admin.lib.php';
require_once DOL_DOCUMENT_ROOT.'/user/class/user.class.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/security.lib.php';

$actor = new User($db);
if ($actor->fetch(1) <= 0) {
	fwrite(STDERR, "cannot fetch admin\n");
	exit(1);
}
$actor->getrights();

$res = activateModule('modWebPortal');
if (is_array($res) && !empty($res['errors'])) {
	fwrite(STDERR, "WARN webportal ".json_encode($res['errors'])."\n");
}

$portal = new User($db);
if ($portal->fetch(0, 'portal') <= 0) {
	$portal = new User($db);
	$portal->login = 'portal';
	$portal->lastname = 'Client portal';
	$portal->firstname = 'GoWifi';
	$portal->admin = 0;
	$portal->entity = 1;
	$pid = $portal->create($actor, 1);
	if ($pid <= 0) {
		fwrite(STDERR, 'create portal user: '.$portal->error."\n");
		exit(1);
	}
	$portal->fetch($pid);
	$pass = dol_hash(random_bytes(16));
	$portal->setPassword($actor, $pass, 0, 1, 0, 1);
}

$portal->admin = 0;
if (property_exists($portal, 'statut')) {
	$portal->statut = 1;
}
$portal->update($actor, 1);

$db->query("DELETE FROM ".$db->prefix()."user_rights WHERE fk_user=".(int) $portal->id);
$db->query(
	"INSERT IGNORE INTO ".$db->prefix()."user_rights (entity, fk_user, fk_id)
	 SELECT 1, ".(int) $portal->id.", id FROM ".$db->prefix()."rights_def
	 WHERE (
	   (module='societe' AND perms IN ('lire','client'))
	   OR (module='facture' AND perms='lire')
	   OR (module='ticket' AND perms IN ('read','write'))
	   OR (module='contrat' AND perms='lire')
	   OR (module='commande' AND perms='lire')
	   OR (module='propal' AND perms='lire')
	   OR (module='ficheinter' AND perms='lire')
	   OR (module='service' AND perms='lire')
	 )"
);

$consts = array(
	'WEBPORTAL_USER_LOGGED' => (string) $portal->id,
	'WEBPORTAL_TITLE' => 'GoWifi account',
	'WEBPORTAL_ROOT_URL' => 'https://gowifi.co.za/account/',
	'WEBPORTAL_INVOICE_LIST_ACCESS' => '1',
	'WEBPORTAL_TICKET_LIST_ACCESS' => '1',
	'WEBPORTAL_FICHEINTER_LIST_ACCESS' => '1',
	'WEBPORTAL_ORDER_LIST_ACCESS' => '1',
	'WEBPORTAL_PROPAL_LIST_ACCESS' => '1',
	'TICKET_ENABLE_PUBLIC_INTERFACE' => '0',
);
foreach ($consts as $name => $value) {
	dolibarr_set_const($db, $name, $value, 'chaine', 0, '', $conf->entity);
}

echo "portal_user=".$portal->id." title=GoWifi account url=/account/ tickets_public=off\n";
