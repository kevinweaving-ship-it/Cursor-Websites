<?php
/**
 * CLI import of the 22 dashboard clients into Dolibarr from real statements.
 * Real invoice refs/dates and real receipt lines. No placeholder credits.
 * Does not write upp.db or accounts.json.
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

function gowifi_sql_payment($bankid, $socid, $facid, $amount, $date, $mode, $note)
{
	global $db, $conf, $user;
	$amount = round((float) $amount, 2);
	$now = $db->idate(dol_now());
	$dp = $db->idate(strtotime(($date ?: '2026-10-07').' 12:00:00'));
	$ok = $db->query("INSERT INTO ".MAIN_DB_PREFIX."paiement (entity, datec, datep, amount, multicurrency_amount, fk_paiement, note, statut, fk_user_creat, fk_bank) VALUES (".((int) $conf->entity).", '".$now."', '".$dp."', ".((float) $amount).", ".((float) $amount).", ".((int) $mode).", '".$db->escape($note)."', 1, ".((int) $user->id).", 0)");
	if (!$ok) {
		return -1;
	}
	$pid = (int) $db->last_insert_id(MAIN_DB_PREFIX.'paiement');
	if ($pid <= 0) {
		return -1;
	}
	$db->query("UPDATE ".MAIN_DB_PREFIX."paiement SET ref='".$pid."' WHERE rowid=".$pid);
	$ok = $db->query("INSERT INTO ".MAIN_DB_PREFIX."paiement_facture (fk_paiement, fk_facture, amount, multicurrency_amount) VALUES (".$pid.", ".((int) $facid).", ".((float) $amount).", ".((float) $amount).")");
	if (!$ok) {
		return -1;
	}
	$d = substr($date ?: '2026-10-07', 0, 10);
	$ok = $db->query("INSERT INTO ".MAIN_DB_PREFIX."bank (datec, datev, dateo, amount, label, fk_account, fk_user_author, fk_type, rappro) VALUES ('".$now."', '".$db->escape($d)."', '".$db->escape($d)."', ".((float) $amount).", '".$db->escape($note)."', ".((int) $bankid).", ".((int) $user->id).", 'VIR', 0)");
	if (!$ok) {
		return -1;
	}
	$bid = (int) $db->last_insert_id(MAIN_DB_PREFIX.'bank');
	$db->query("UPDATE ".MAIN_DB_PREFIX."paiement SET fk_bank=".$bid." WHERE rowid=".$pid);
	$db->query("INSERT INTO ".MAIN_DB_PREFIX."bank_url (fk_bank, url_id, url, label, type) VALUES (".$bid.", ".$pid.", '/compta/paiement/card.php?id=".$pid."', '".$db->escape($note)."', 'payment')");
	$db->query("INSERT INTO ".MAIN_DB_PREFIX."bank_url (fk_bank, url_id, url, label, type) VALUES (".$bid.", ".((int) $socid).", '/societe/card.php?socid=".$socid."', 'company', 'company')");
	return $pid;
}

function gowifi_add_payment($bankid, $socid, $facid, $amount, $date, $mode, $note)
{
	global $db, $user;
	$amount = round((float) $amount, 2);
	if ($amount <= 0.004) {
		return 1;
	}
	$pay = new Paiement($db);
	$pay->datepaye = strtotime(($date ?: '2026-10-07').' 12:00:00');
	$pay->paiementid = $mode;
	$pay->amounts = array((int) $facid => number_format($amount, 2, '.', ''));
	$pay->note_public = $note;
	$pid = $pay->create($user, 1);
	if ($pid <= 0) {
		$pid = $pay->create($user, 0);
	}
	if ($pid <= 0) {
		return gowifi_sql_payment($bankid, $socid, $facid, $amount, $date, $mode, $note);
	}
	$br = $pay->addPaymentToBank($user, 'payment', '(CustomerInvoicePayment)', $bankid, '', '');
	if ($br <= 0) {
		return gowifi_sql_payment($bankid, $socid, $facid, $amount, $date, $mode, $note);
	}
	return $pid;
}

// Wipe previous customer books only. Keep Openserve, bank account, modules.
foreach (array(
	"DELETE FROM ".MAIN_DB_PREFIX."paiement_facture",
	"DELETE FROM ".MAIN_DB_PREFIX."paiement",
	"DELETE FROM ".MAIN_DB_PREFIX."bank_url",
	"DELETE FROM ".MAIN_DB_PREFIX."bank WHERE fk_account=".(int) $bankid,
	"DELETE FROM ".MAIN_DB_PREFIX."societe_remise_except",
	"DELETE FROM ".MAIN_DB_PREFIX."facturedet",
	"DELETE FROM ".MAIN_DB_PREFIX."facture",
	"DELETE cs FROM ".MAIN_DB_PREFIX."categorie_societe cs JOIN ".MAIN_DB_PREFIX."societe s ON s.rowid=cs.fk_soc WHERE s.client=1 AND s.fournisseur=0",
	"DELETE e FROM ".MAIN_DB_PREFIX."societe_extrafields e JOIN ".MAIN_DB_PREFIX."societe s ON s.rowid=e.fk_object WHERE s.client=1 AND s.fournisseur=0",
	"DELETE FROM ".MAIN_DB_PREFIX."societe WHERE client=1 AND fournisseur=0",
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
$paycount = 0;

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
		$soc->note_private = 'GoWiFi statement import · '.$cli['access'].' · '.$cli['pay'].' · '.$cli['package'];
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
	$cat = (stripos((string) ($cli['access'] ?? ''), 'fibre') !== false) ? 2 : 1;
	$db->query("INSERT IGNORE INTO ".MAIN_DB_PREFIX."categorie_societe (fk_categorie, fk_soc) VALUES (".$cat.", ".$socid.")");

	$facids = array();
	$remain = array();
	$order = array();
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
		$facids[$inv['ref']] = (int) $facid;
		$remain[$inv['ref']] = round((float) $inv['amount'], 2);
		$order[] = array('ref' => $inv['ref'], 'date' => $inv['date'], 'id' => (int) $facid);
	}
	usort($order, function ($a, $b) {
		return strcmp($a['date'].$a['ref'], $b['date'].$b['ref']);
	});
	$latest = $order ? $order[count($order) - 1] : null;

	$unapplied = array();
	foreach (($cli['payments'] ?? array()) as $pmt) {
		$amt = round((float) $pmt['amount'], 2);
		$ref = (string) ($pmt['ref'] ?? '');
		$mode = (($pmt['method'] ?? $cli['pay']) === 'D/O') ? $mode_pre : $mode_vir;
		$note = $pmt['what'] ?: ('Receipt '.$cli['name']);
		$datep = $pmt['date'] ?? $payload['as_at'];
		if ($ref !== '' && isset($facids[$ref]) && $remain[$ref] > 0.004) {
			$take = round(min($amt, $remain[$ref]), 2);
			$pid = gowifi_add_payment($bankid, $socid, $facids[$ref], $take, $datep, $mode, $note);
			if ($pid <= 0) {
				fwrite(STDERR, "FAIL payment ".$cli['name']." ".$ref."\n");
				exit(9);
			}
			$remain[$ref] = round($remain[$ref] - $take, 2);
			$amt = round($amt - $take, 2);
			$paycount++;
		}
		if ($amt > 0.004) {
			$unapplied[] = array('amount' => $amt, 'date' => $datep, 'mode' => $mode, 'note' => $note);
		}
	}
	foreach ($unapplied as &$u) {
		foreach ($order as $inv) {
			if ($u['amount'] <= 0.004) {
				break;
			}
			$ref = $inv['ref'];
			if ($remain[$ref] <= 0.004) {
				continue;
			}
			$take = round(min($u['amount'], $remain[$ref]), 2);
			$pid = gowifi_add_payment($bankid, $socid, $inv['id'], $take, $u['date'], $u['mode'], $u['note']);
			if ($pid <= 0) {
				fwrite(STDERR, "FAIL leftover-apply ".$cli['name']." ".$ref."\n");
				exit(9);
			}
			$remain[$ref] = round($remain[$ref] - $take, 2);
			$u['amount'] = round($u['amount'] - $take, 2);
			$paycount++;
		}
	}
	unset($u);
	foreach ($unapplied as $u) {
		if ($u['amount'] <= 0.004 || !$latest) {
			continue;
		}
		$pid = gowifi_add_payment($bankid, $socid, $latest['id'], $u['amount'], $u['date'], $u['mode'], $u['note']);
		if ($pid <= 0) {
			fwrite(STDERR, "FAIL overpay ".$cli['name']."\n");
			exit(9);
		}
		$paycount++;
	}

	$created[] = $cli['name'];
}

// Any auto-created unused credit objects are placeholders — remove them.
$db->query("DELETE FROM ".MAIN_DB_PREFIX."societe_remise_except WHERE description='(EXCESS RECEIVED)' OR fk_facture IS NULL");

$q = $db->query("SELECT ROUND(SUM(total_ttc),2) AS billed FROM ".MAIN_DB_PREFIX."facture WHERE entity=".(int) $conf->entity);
$billed = (float) $db->fetch_object($q)->billed;
$q = $db->query("SELECT ROUND(SUM(amount),2) AS paid FROM ".MAIN_DB_PREFIX."paiement WHERE entity=".(int) $conf->entity);
$paid = (float) ($db->fetch_object($q)->paid ?? 0);
$q = $db->query("SELECT s.nom,
	ROUND(SUM(f.total_ttc),2) billed,
	ROUND(COALESCE(SUM(p.paye),0),2) paid
	FROM ".MAIN_DB_PREFIX."societe s
	JOIN ".MAIN_DB_PREFIX."facture f ON f.fk_soc=s.rowid
	LEFT JOIN (
		SELECT pf.fk_facture, SUM(pf.amount) paye
		FROM ".MAIN_DB_PREFIX."paiement_facture pf
		GROUP BY pf.fk_facture
	) p ON p.fk_facture=f.rowid
	WHERE s.client=1
	GROUP BY s.rowid, s.nom ORDER BY s.nom");
$by = array();
foreach ($payload['clients'] as $cli) {
	$by[$cli['name']] = $cli;
}
$failed = 0;
$ar = 0.0;
$adv = 0.0;
while ($q && ($row = $db->fetch_object($q))) {
	$cli = $by[$row->nom] ?? null;
	$due = round(((float) $row->billed) - ((float) $row->paid), 2);
	if ($due > 0.004) {
		$ar = round($ar + $due, 2);
	}
	if ($due < -0.004) {
		$adv = round($adv + (-$due), 2);
	}
	$pass = $cli
		&& abs((float) $row->billed - $cli['billed']) < 0.02
		&& abs((float) $row->paid - $cli['paid']) < 0.02
		&& abs($due - $cli['due']) < 0.02;
	echo ($pass ? "PASS " : "FAIL ").$row->nom." billed ".$row->billed." paid ".$row->paid." due ".$due." want_billed ".($cli['billed'] ?? '?')." want_paid ".($cli['paid'] ?? '?')." want_due ".($cli['due'] ?? '?')."\n";
	if (!$pass) {
		$failed++;
	}
}
$q2 = $db->query("SELECT COUNT(*) n FROM ".MAIN_DB_PREFIX."societe_remise_except");
$credits = (int) $db->fetch_object($q2)->n;
echo ($credits === 0 ? "PASS " : "FAIL ")."no-placeholder-credits ".$credits."\n";
if ($credits !== 0) {
	$failed++;
}
$openserve = $db->query("SELECT COUNT(*) n FROM ".MAIN_DB_PREFIX."societe WHERE nom='Openserve' AND fournisseur=1");
$on = (int) $db->fetch_object($openserve)->n;
echo ($on === 1 ? "PASS " : "FAIL ")."openserve-kept ".$on."\n";
if ($on !== 1) {
	$failed++;
}
$paltco = $db->query("SELECT COUNT(*) n FROM ".MAIN_DB_PREFIX."societe WHERE nom LIKE '%Paltco%'");
$pn = (int) $db->fetch_object($paltco)->n;
echo ($pn === 0 ? "PASS " : "FAIL ")."paltco-not-imported ".$pn."\n";
if ($pn !== 0) {
	$failed++;
}

$net = round($ar - $adv, 2);
$want = $payload['controls'];
$got = array(
	'billed' => $billed,
	'paid' => $paid,
	'ar' => $ar,
	'advances' => $adv,
	'net' => $net,
	'clients' => count($created),
	'payments' => $paycount,
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
echo ($ok ? "PASS " : "FAIL ")."controls-match\n";
if (!$ok) {
	$failed++;
}
echo $failed ? "FAIL client-rows $failed\n" : "PASS all-22\n";
exit($failed ? 13 : 0);
