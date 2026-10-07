<?php
/**
 * CLI trial import into Dolibarr 24.0.2. No HTTP. No upp.db writes.
 */
if (php_sapi_name() !== 'cli') {
	fwrite(STDERR, "cli only\n");
	exit(1);
}

define('NOSESSION', 1);
$_SERVER['HTTP_HOST'] = 'gowifi.co.za';
$_SERVER['HTTPS'] = 'on';
$_SERVER['SERVER_NAME'] = 'gowifi.co.za';
$_SERVER['DOCUMENT_ROOT'] = '/opt/dolibarr/htdocs';
chdir('/opt/dolibarr/htdocs');
require_once '/opt/dolibarr/htdocs/master.inc.php';
require_once DOL_DOCUMENT_ROOT.'/core/lib/admin.lib.php';
require_once DOL_DOCUMENT_ROOT.'/societe/class/societe.class.php';
require_once DOL_DOCUMENT_ROOT.'/compta/facture/class/facture.class.php';
require_once DOL_DOCUMENT_ROOT.'/compta/paiement/class/paiement.class.php';
require_once DOL_DOCUMENT_ROOT.'/compta/bank/class/account.class.php';
require_once DOL_DOCUMENT_ROOT.'/core/class/discount.class.php';
require_once DOL_DOCUMENT_ROOT.'/user/class/user.class.php';

global $db, $conf, $user, $langs;

$user = new User($db);
if ($user->fetch('', 'admin') <= 0) {
	fwrite(STDERR, "FAIL no-admin-user\n");
	exit(4);
}
$user->getrights();

foreach (array('modSociete', 'modFacture', 'modBanque', 'modApi') as $mod) {
	$res = activateModule($mod);
	if (is_array($res) && !empty($res['errors'])) {
		fwrite(STDERR, "WARN activate $mod ".json_encode($res['errors'])."\n");
	}
}

dolibarr_set_const($db, 'MAIN_INFO_SOCIETE_NOM', 'GoWiFi', 'chaine', 0, '', $conf->entity);
dolibarr_set_const($db, 'MAIN_INFO_SOCIETE_COUNTRY', '205', 'chaine', 0, '', $conf->entity);
dolibarr_set_const($db, 'MAIN_MONNAIE', 'ZAR', 'chaine', 0, '', $conf->entity);
dolibarr_set_const($db, 'MAIN_INFO_TVAINTRA', '', 'chaine', 0, '', $conf->entity);
dolibarr_set_const($db, 'FACTURE_ADDON', 'mod_facture_terre', 'chaine', 0, '', $conf->entity);

$bankid = 0;
$sql = "SELECT rowid FROM ".MAIN_DB_PREFIX."bank_account WHERE ref='FNB' AND entity=".(int) $conf->entity;
$resql = $db->query($sql);
if ($resql && ($obj = $db->fetch_object($resql))) {
	$bankid = (int) $obj->rowid;
}
if (!$bankid) {
	$acc = new Account($db);
	$acc->ref = 'FNB';
	$acc->label = 'FNB current';
	$acc->courant = Account::TYPE_CURRENT;
	$acc->type = Account::TYPE_CURRENT;
	$acc->currency_code = 'ZAR';
	$acc->country_id = 205;
	$acc->country_code = 'ZA';
	$acc->state_id = 0;
	$acc->rappro = 1;
	$acc->date_solde = dol_now();
	$acc->solde = 0;
	$bankid = $acc->create($user, 0);
	if ($bankid <= 0) {
		fwrite(STDERR, "FAIL bank ".$acc->error."\n");
		exit(5);
	}
}

// Trial rerun: wipe previous customer import only. Keep admin, bank, modules.
foreach (array(
	"DELETE FROM ".MAIN_DB_PREFIX."paiement_facture",
	"DELETE FROM ".MAIN_DB_PREFIX."paiement",
	"DELETE FROM ".MAIN_DB_PREFIX."bank WHERE fk_account=".(int) $bankid,
	"DELETE FROM ".MAIN_DB_PREFIX."societe_remise_except",
	"DELETE FROM ".MAIN_DB_PREFIX."facturedet",
	"DELETE FROM ".MAIN_DB_PREFIX."facture",
	"DELETE FROM ".MAIN_DB_PREFIX."societe_extrafields",
	"DELETE FROM ".MAIN_DB_PREFIX."societe",
) as $wipe) {
	if (!$db->query($wipe)) {
		fwrite(STDERR, "FAIL wipe ".$db->lasterror()."\n");
		exit(6);
	}
}

$jsonpath = getenv('GOWIFI_TRIAL_JSON') ?: '/tmp/gowifi-dolibarr-trial.json';
$payload = json_decode(file_get_contents($jsonpath), true);
if (!$payload || empty($payload['clients'])) {
	fwrite(STDERR, "FAIL no-payload\n");
	exit(6);
}

$mode_vir = 2;
$mode_pre = 3;
$created = array();

foreach ($payload['clients'] as $cli) {
	$soc = new Societe($db);
	$socid = 0;
	$find = $db->query("SELECT rowid FROM ".MAIN_DB_PREFIX."societe WHERE nom='".$db->escape($cli['name'])."' AND entity=".(int) $conf->entity);
	if ($find && ($obj = $db->fetch_object($find))) {
		$socid = (int) $obj->rowid;
		$soc->fetch($socid);
	}
	if ($socid <= 0) {
		$soc = new Societe($db);
		$soc->name = $cli['name'];
		$soc->client = 1;
		$soc->fournisseur = 0;
		$soc->tva_assuj = 0;
		$soc->country_id = 205;
		$soc->idprof1 = $cli['b_number'];
		$soc->array_options = array();
		$soc->note_private = 'GoWiFi trial import · '.$cli['access'].' · '.$cli['pay'].' · '.$cli['package'];
		if (!empty($cli['unpaid_do'])) {
			$bits = array('Netcash unpaid D/O history (event amounts, not current due):');
			foreach ($cli['unpaid_do'] as $ev) {
				$bits[] = $ev['date'].' R'.number_format($ev['amount'], 2, '.', '').' '.$ev['note'];
			}
			$soc->note_private .= "\n".implode("\n", $bits);
		}
		$socid = $soc->create($user);
		if ($socid <= 0) {
			fwrite(STDERR, "FAIL thirdparty ".$cli['name']." ".$soc->error."\n");
			exit(7);
		}
	}
	if ($socid <= 0) {
		fwrite(STDERR, "FAIL socid ".$cli['name']."\n");
		exit(7);
	}

	$facids = array();
	foreach ($cli['invoices'] as $inv) {
		$fac = new Facture($db);
		$fac->socid = $socid;
		$fac->type = Facture::TYPE_STANDARD;
		$fac->date = strtotime($inv['date'].' 12:00:00');
		$fac->date_lim_reglement = $fac->date;
		$fac->cond_reglement_id = 0;
		$fac->mode_reglement_id = ($cli['pay'] === 'D/O') ? $mode_pre : $mode_vir;
		$fac->ref_ext = $inv['ref'];
		$fac->ref_client = $inv['ref'];
		$fac->note_public = $inv['what'];
		$facid = $fac->create($user);
		if ($facid <= 0) {
			fwrite(STDERR, "FAIL invoice ".$inv['ref']." ".$fac->error." ".json_encode($fac->errors)."\n");
			exit(8);
		}
		$lid = $fac->addline($inv['what'] ?: ('Invoice '.$inv['ref']), $inv['amount'], 1, 0, 0, 0, 0, 0, '', '', 0, 0, 0, 'HT', 0, 1);
		if ($lid <= 0) {
			fwrite(STDERR, "FAIL line ".$inv['ref']." ".$fac->error."\n");
			exit(8);
		}
		$vr = $fac->validate($user, $inv['ref']);
		if ($vr < 0) {
			$db->query("UPDATE ".MAIN_DB_PREFIX."facture SET ref='".$db->escape($inv['ref'])."', fk_statut=1 WHERE rowid=".(int) $facid);
		}
		$fac->fetch($facid);
		$facids[$inv['ref']] = array('id' => (int) $facid, 'to_pay' => (float) $inv['to_pay']);
	}

	$amounts = array();
	foreach ($facids as $ref => $info) {
		if ($info['to_pay'] > 0.004) {
			$amounts[$info['id']] = (string) number_format($info['to_pay'], 2, '.', '');
		}
	}
	if ($amounts) {
		$pay = new Paiement($db);
		$pay->datepaye = strtotime($payload['as_at'].' 12:00:00');
		$pay->paiementid = ($cli['pay'] === 'D/O') ? $mode_pre : $mode_vir;
		$pay->amounts = $amounts;
		$pay->note_public = 'GoWiFi statement allocations '.$cli['name'];
		$pid = $pay->create($user, 1);
		if ($pid <= 0) {
			fwrite(STDERR, "FAIL payment ".$cli['name']." ".$pay->error." ".json_encode($pay->errors)."\n");
			exit(9);
		}
		$br = $pay->addPaymentToBank($user, 'payment', '(CustomerInvoicePayment)', $bankid, '', '');
		if ($br <= 0) {
			fwrite(STDERR, "FAIL bankline ".$cli['name']." ".$pay->error."\n");
			exit(10);
		}
	}

	if ($cli['advance'] > 0.004) {
		$disc = new DiscountAbsolute($db);
		$disc->socid = $socid;
		$disc->fk_soc = $socid;
		$disc->fk_facture_source = 0;
		$disc->amount_ht = $cli['advance'];
		$disc->amount_tva = 0;
		$disc->amount_ttc = $cli['advance'];
		$disc->tva_tx = 0;
		$disc->description = '(EXCESS RECEIVED)';
		$did = $disc->create($user);
		if ($did <= 0) {
			fwrite(STDERR, "FAIL advance ".$cli['name']." ".$disc->error."\n");
			exit(11);
		}
	}

	$created[] = $cli['name'];
}

// Validate Dolibarr totals against the statement controls.
$q = $db->query("SELECT ROUND(SUM(total_ttc),2) AS billed FROM ".MAIN_DB_PREFIX."facture WHERE entity=".(int) $conf->entity);
$billed = (float) $db->fetch_object($q)->billed;
$q = $db->query("SELECT ROUND(SUM(amount),2) AS paid FROM ".MAIN_DB_PREFIX."paiement WHERE entity=".(int) $conf->entity);
$paid_row = $db->fetch_object($q);
$paid_pmt = (float) ($paid_row->paid ?? 0);
$q = $db->query("SELECT ROUND(SUM(amount_ttc),2) AS adv FROM ".MAIN_DB_PREFIX."societe_remise_except WHERE fk_facture IS NULL AND entity=".(int) $conf->entity);
$adv_row = $db->fetch_object($q);
$adv = (float) ($adv_row->adv ?? 0);
$q = $db->query("SELECT ROUND(SUM(f.total_ttc - IFNULL(p.paye,0)),2) AS ar
	FROM ".MAIN_DB_PREFIX."facture f
	LEFT JOIN (
		SELECT pf.fk_facture, SUM(pf.amount) paye
		FROM ".MAIN_DB_PREFIX."paiement_facture pf
		GROUP BY pf.fk_facture
	) p ON p.fk_facture = f.rowid
	WHERE f.entity=".(int) $conf->entity);
$ar = (float) $db->fetch_object($q)->ar;
$paid = round($paid_pmt + $adv, 2);
$net = round($ar - $adv, 2);

$want = $payload['controls'];
$got = array(
	'billed' => $billed,
	'paid' => $paid,
	'ar' => $ar,
	'advances' => $adv,
	'net' => $net,
	'clients' => count($created),
);
echo "DOLIBARR ".json_encode($got)."\n";
$ok = (
	abs($billed - $want['billed']) < 0.02
	&& abs($paid - $want['paid']) < 0.02
	&& abs($ar - $want['ar']) < 0.02
	&& abs($adv - $want['advances']) < 0.02
	&& abs($net - $want['net']) < 0.02
	&& count($created) === 22
);
if (!$ok) {
	echo "FAIL dolibarr-controls want ".json_encode($want)."\n";
	exit(12);
}
echo "PASS controls-match\n";

$q = $db->query("SELECT s.nom, ROUND(SUM(f.total_ttc),2) billed,
	ROUND(SUM(f.total_ttc - IFNULL(p.paye,0)),2) remain
	FROM ".MAIN_DB_PREFIX."societe s
	JOIN ".MAIN_DB_PREFIX."facture f ON f.fk_soc=s.rowid
	LEFT JOIN (
		SELECT pf.fk_facture, SUM(pf.amount) paye
		FROM ".MAIN_DB_PREFIX."paiement_facture pf
		GROUP BY pf.fk_facture
	) p ON p.fk_facture=f.rowid
	GROUP BY s.rowid, s.nom ORDER BY s.nom");
$by = array();
foreach ($payload['clients'] as $cli) {
	$by[$cli['name']] = $cli;
}
$failed = 0;
while ($q && ($row = $db->fetch_object($q))) {
	$cli = $by[$row->nom] ?? null;
	$remain = (float) $row->remain;
	$want_remain = $cli ? (float) $cli['ar'] : null;
	$pass = $cli && abs((float) $row->billed - $cli['billed']) < 0.02 && abs($remain - $want_remain) < 0.02;
	echo ($pass ? "PASS " : "FAIL ").$row->nom." billed ".$row->billed." remain ".$remain." want_billed ".($cli['billed'] ?? '?')." want_ar ".($want_remain ?? '?')."\n";
	if (!$pass) {
		$failed++;
	}
}
$q2 = $db->query("SELECT s.nom, ROUND(SUM(r.amount_ttc),2) adv
	FROM ".MAIN_DB_PREFIX."societe_remise_except r
	JOIN ".MAIN_DB_PREFIX."societe s ON s.rowid=r.fk_soc
	WHERE r.fk_facture IS NULL
	GROUP BY s.rowid, s.nom");
$adv_got = array();
while ($q2 && ($row = $db->fetch_object($q2))) {
	$adv_got[$row->nom] = (float) $row->adv;
}
foreach ($payload['clients'] as $cli) {
	$g = $adv_got[$cli['name']] ?? 0.0;
	$pass = abs($g - $cli['advance']) < 0.02;
	echo ($pass ? "PASS " : "FAIL ").$cli['name']." advance ".$g." want ".$cli['advance']."\n";
	if (!$pass) {
		$failed++;
	}
}
$paltco = $db->query("SELECT COUNT(*) n FROM ".MAIN_DB_PREFIX."societe WHERE nom LIKE '%Paltco%'");
$pn = (int) $db->fetch_object($paltco)->n;
echo ($pn === 0 ? "PASS " : "FAIL ")."paltco-not-imported ".$pn."\n";
if ($pn !== 0) {
	$failed++;
}
echo $failed ? "FAIL client-rows $failed\n" : "PASS all-22\n";
exit($failed ? 13 : 0);
