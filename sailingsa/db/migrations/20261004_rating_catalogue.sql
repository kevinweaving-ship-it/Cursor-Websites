-- Versioned rating catalogue. Does not alter classes, class_aliases, results,
-- ranking_standings, or standings_recalc_queue, and does not create classes.
-- Rating numbers are the RYA Portsmouth Number List 2026, version 4.
-- Class links are not inserted here. Review py_rating/published/rya_py_2026_class_review.json first.

BEGIN;

CREATE TABLE IF NOT EXISTS public.rating_system (
    system_code text PRIMARY KEY,
    system_name text NOT NULL,
    publisher text NOT NULL,
    scale_numerator integer NOT NULL CHECK (scale_numerator > 0),
    description text NOT NULL
);

CREATE TABLE IF NOT EXISTS public.rating_publication (
    publication_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    system_code text NOT NULL REFERENCES public.rating_system (system_code),
    version_label text NOT NULL,
    version_number text NOT NULL,
    announced_on date,
    source_last_update date,
    source_last_update_printed text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    source_title text NOT NULL,
    source_url text NOT NULL,
    announcement_url text NOT NULL,
    scheme_url text NOT NULL,
    publisher text NOT NULL,
    formula text NOT NULL,
    rounding_rule text NOT NULL,
    notes text NOT NULL,
    CONSTRAINT rating_publication_version_unique UNIQUE (system_code, version_label, version_number),
    CONSTRAINT rating_publication_dates CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE IF NOT EXISTS public.rating_catalogue_entry (
    rating_entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    publication_id bigint NOT NULL REFERENCES public.rating_publication (publication_id),
    list_section text NOT NULL CHECK (list_section IN ('dinghy_base', 'multihull_base', 'experimental')),
    source_class_id text NOT NULL,
    source_class_name text NOT NULL,
    crew_count integer CHECK (crew_count IS NULL OR crew_count > 0),
    rig text,
    spinnaker text,
    variant text NOT NULL DEFAULT '',
    rating_value integer NOT NULL CHECK (rating_value > 0),
    change_from_previous integer,
    source_notes text NOT NULL DEFAULT '',
    CONSTRAINT rating_catalogue_entry_source_unique UNIQUE (publication_id, source_class_id)
);

CREATE TABLE IF NOT EXISTS public.rating_class_review (
    review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rating_entry_id bigint NOT NULL REFERENCES public.rating_catalogue_entry (rating_entry_id),
    match_status text NOT NULL CHECK (match_status IN ('matched', 'unmatched', 'ambiguous')),
    class_id integer REFERENCES public.classes (class_id),
    candidate_class_ids integer[] NOT NULL DEFAULT '{}',
    matched_on text[] NOT NULL DEFAULT '{}',
    review_notes text NOT NULL DEFAULT '',
    reviewed_by text,
    reviewed_at timestamptz,
    CONSTRAINT rating_class_review_entry_unique UNIQUE (rating_entry_id),
    CONSTRAINT rating_class_review_status_class CHECK (
        (match_status = 'matched' AND class_id IS NOT NULL)
        OR (match_status IN ('unmatched', 'ambiguous') AND class_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.rating_time_application (
    application_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rating_entry_id bigint NOT NULL REFERENCES public.rating_catalogue_entry (rating_entry_id),
    publication_id bigint NOT NULL REFERENCES public.rating_publication (publication_id),
    class_id integer REFERENCES public.classes (class_id),
    result_id bigint REFERENCES public.results (result_id),
    system_code text NOT NULL,
    version_label text NOT NULL,
    version_number text NOT NULL,
    source_class_id text NOT NULL,
    source_class_name text NOT NULL,
    rating_value_used integer NOT NULL CHECK (rating_value_used > 0),
    elapsed_seconds numeric NOT NULL CHECK (elapsed_seconds >= 0),
    corrected_seconds_exact numeric NOT NULL,
    corrected_seconds integer NOT NULL CHECK (corrected_seconds >= 0),
    formula text NOT NULL,
    rounding_rule text NOT NULL,
    calculated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rating_time_application_result_idx
    ON public.rating_time_application (result_id);

INSERT INTO public.rating_system (system_code, system_name, publisher, scale_numerator, description)
VALUES (
    'RYA_PY',
    'Portsmouth Yardstick',
    'Royal Yachting Association',
    1000,
    'UK Portsmouth Number. Corrected time = elapsed seconds * 1000 / PY number.'
)
ON CONFLICT (system_code) DO NOTHING;

INSERT INTO public.rating_publication (
    system_code, version_label, version_number, announced_on, source_last_update,
    source_last_update_printed, effective_from, effective_to, source_title, source_url,
    announcement_url, scheme_url, publisher, formula, rounding_rule, notes
)
SELECT
    'RYA_PY', '2026', '4', DATE '2026-02-21', DATE '2026-04-22',
    '22/04/206', DATE '2026-04-22', NULL,
    'Portsmouth Number List 2026',
    'https://assets.rya.org.uk/assetbank-rya-assets/action/directLinkImage?assetId=50500',
    'https://www.rya.org.uk/news/portsmouth-yardstick-numbers-2026/',
    'https://www.rya.org.uk/racing/portsmouth-yardstick',
    'Royal Yachting Association',
    'elapsed_seconds * 1000 / py_number',
    'nearest_second_half_up',
'National base list, version 4. The PDF prints Last update 22/04/206; that is recorded as printed and read as 22 April 2026. Dinghy base, multihull base, and experimental numbers from this file are included. The separate Limited Data List is not in this file. Rig S is sloop and U is una. Spinnaker 0 is none, A is asymmetric, C is conventional. SCHRS numbers convert by the factor 666 printed on the multihull page; those conversions are not stored as catalogue rows.'
WHERE NOT EXISTS (
    SELECT 1 FROM public.rating_publication
    WHERE system_code = 'RYA_PY' AND version_label = '2026' AND version_number = '4'
);

INSERT INTO public.rating_catalogue_entry (
    publication_id, list_section, source_class_id, source_class_name, crew_count,
    rig, spinnaker, variant, rating_value, change_from_previous, source_notes
)
SELECT publication_id, list_section, source_class_id, source_class_name, crew_count,
       rig, spinnaker, variant, rating_value, change_from_previous, source_notes
FROM public.rating_publication p
JOIN (VALUES

('dinghy_base', '6', '2.4mR', 1, 'S', '0', '', 1235, -9, ''),
('dinghy_base', '221', '2000', 2, 'S', 'A', '', 1122, 1, ''),
('dinghy_base', '7', '29er', 2, 'S', 'A', '', 900, 0, ''),
('dinghy_base', '223', '4000', 2, 'S', 'A', '', 926, 3, ''),
('dinghy_base', '12', '420', 2, 'S', 'C', '', 1110, 0, ''),
('dinghy_base', '17', '505', 2, 'S', 'C', '', 892, -4, ''),
('dinghy_base', '22', 'ALBACORE', 2, 'S', '0', '', 1037, 0, ''),
('dinghy_base', '25', 'ALTO', 2, 'S', 'A', '', 910, -11, ''),
('dinghy_base', '28', 'B14', 2, 'S', 'A', '', 858, 0, ''),
('dinghy_base', '34', 'BLAZE', 1, 'U', '0', '', 1030, 0, ''),
('dinghy_base', '44', 'BRITISH MOTH', 1, 'U', '0', '', 1160, -5, ''),
('dinghy_base', '46', 'BUZZ', 2, 'S', 'A', '', 1009, 3, 'MOVED FROM EXPERIMENTAL LIST'),
('dinghy_base', '50', 'BYTE CII', 1, 'U', '0', '', 1123, -6, ''),
('dinghy_base', '62', 'COMET', 1, 'U', '0', '', 1208, 0, ''),
('dinghy_base', '64', 'COMET XTRA', 1, 'U', '0', '', 1210, 0, 'MOVED FROM LIMITED DATA LIST'),
('dinghy_base', '69', 'COMET TRIO MK 1', 2, 'S', 'A', '', 1082, -6, 'CLUBS TO DISTINGUISH BETWEEN MK 1 AND MK 2 RIGS ON RETURNS'),
('dinghy_base', '70', 'COMET TRIO MK 2', 2, 'S', 'A', '', 1053, 0, 'CLUBS TO DISTINGUISH BETWEEN MK 1 AND MK 2 RIGS ON RETURNS'),
('dinghy_base', '71', 'CONTENDER', 1, 'U', '0', '', 973, 4, ''),
('dinghy_base', '81', 'DEVOTI D-ONE', 1, 'U', 'A', '', 957, 2, ''),
('dinghy_base', '82', 'DEVOTI D-ZERO', 1, 'U', '0', '', 1029, 0, ''),
('dinghy_base', '108', 'ENTERPRISE', 2, 'S', '0', '', 1137, 0, ''),
('dinghy_base', '111', 'EUROPE', 1, 'U', '0', '', 1140, 0, ''),
('dinghy_base', '132', 'FINN', 1, 'U', '0', '', 1049, 0, ''),
('dinghy_base', '133', 'FIREBALL', 2, 'S', 'C', '', 960, 1, ''),
('dinghy_base', '135', 'FIREFLY', 2, 'S', '0', '', 1178, 4, ''),
('dinghy_base', '140', 'FLYING FIFTEEN CLASSIC (1-2700)', 2, 'S', 'C', 'Classic (1-2700)', 1079, 0, 'NEW TO LIST 2026'),
('dinghy_base', '141', 'FLYING FIFTEEN SILVER (2701-3400)', 2, 'S', 'C', 'Silver (2701-3400)', 1051, 0, 'NEW TO LIST 2026'),
('dinghy_base', '142', 'FlYING FIFTEEN', 2, 'S', 'C', '', 1028, 0, ''),
('dinghy_base', '148', 'FUSION PRO', 1, 'U', '0', '', 1281, -9, ''),
('dinghy_base', '153', 'GP14', 2, 'S', 'C', '', 1145, 4, ''),
('dinghy_base', '155', 'GRADUATE', 2, 'S', '0', '', 1110, 10, ''),
('dinghy_base', '156', 'GULL', 2, 'S', 'C', '', 1385, 0, 'MOVED FROM LIMITED DATA LIST'),
('dinghy_base', '158', 'HADRON H2', 1, 'U', '0', '', 1045, 0, ''),
('dinghy_base', '182', 'HORNET', 2, 'S', 'C', '', 950, -5, ''),
('dinghy_base', '189', 'ILCA 4 / Laser 4.7', 1, 'U', '0', '', 1218, 2, ''),
('dinghy_base', '190', 'ILCA 6 / Laser Radial', 1, 'U', '0', '', 1156, 2, ''),
('dinghy_base', '191', 'ILCA 7 / Laser', 1, 'U', '0', '', 1103, -1, ''),
('dinghy_base', '192', 'ILLUSION', 1, 'S', 'C', '', 1285, -9, 'MOVED FROM LIMITED DATA LIST'),
('dinghy_base', '204', 'K1', 1, 'S', '0', '', 1060, -5, ''),
('dinghy_base', '319', 'K6', 2, 'S', 'A', '', 900, -10, ''),
('dinghy_base', '206', 'KESTREL', 2, 'S', 'C', '', 1042, 0, ''),
('dinghy_base', '213', 'LARK', 2, 'S', 'C', '', 1060, 0, ''),
('dinghy_base', '233', 'LASER STRATOS CENTREBOARD', 2, 'S', 'A', '', 1108, 5, 'MOVED FROM LIMITED DATA LIST'),
('dinghy_base', '239', 'LIGHTNING 368', 1, 'U', '0', '', 1171, 3, ''),
('dinghy_base', '245', 'MEGABYTE', 1, 'U', '0', '', 1058, -2, ''),
('dinghy_base', '250', 'MERLIN ROCKET', 2, 'S', 'C', '', 980, -3, ''),
('dinghy_base', '252', 'MIRACLE', 2, 'S', 'C', '', 1196, 0, ''),
('dinghy_base', '253', 'MIRROR', 2, 'S', 'C', '', 1364, -4, ''),
('dinghy_base', '254', 'MIRROR - SINGLEHANDED WITH SPINNAKER', 1, 'S', 'C', 'SINGLEHANDED WITH SPINNAKER', 1364, 4, 'MOVED FROM LIMITED DATA LIST'),
('dinghy_base', '255', 'MIRROR SINGLEHANDED NO SPINNAKER', 1, 'S', '0', 'SINGLEHANDED NO SPINNAKER', 1376, 1, ''),
('dinghy_base', '257', 'MUSTO SKIFF', 1, 'U', 'A', '', 830, -4, ''),
('dinghy_base', '259', 'NATIONAL 12', 2, 'S', '0', '', 1070, 0, 'CLUBS TO DISTINGUISH BETWEEN DIFFERENT'),
('dinghy_base', '280', 'OK', 1, 'U', '0', '', 1092, -3, ''),
('dinghy_base', '282', 'OPTIMIST', 1, 'U', '0', '', 1629, -2, ''),
('dinghy_base', '283', 'OSPREY', 2, 'S', 'C', '', 932, 0, ''),
('dinghy_base', '288', 'PHANTOM', 1, 'U', '0', '', 998, 0, ''),
('dinghy_base', '299', 'ROOSTER 8.1', 1, 'U', '0', '', 1016, -5, ''),
('dinghy_base', '311', 'RS AERO 5', 1, 'U', '0', '', 1141, 2, ''),
('dinghy_base', '455', 'RS AERO 6', 1, 'U', '0', '', 1098, -1, ''),
('dinghy_base', '312', 'RS AERO 7', 1, 'U', '0', '', 1062, -1, ''),
('dinghy_base', '313', 'RS AERO 9', 1, 'U', '0', '', 1005, 0, ''),
('dinghy_base', '318', 'RS FEVA XL', 2, 'S', 'A', '', 1248, 4, 'CLUBS TO DISTINGUISH BETWEEN S AND XL VARIANTS ON RETURNS'),
('dinghy_base', '324', 'RS TERA PRO', 1, 'U', '0', '', 1368, -2, ''),
('dinghy_base', '323', 'RS TERA SPORT', 1, 'U', '0', '', 1452, -3, ''),
('dinghy_base', '325', 'RS VAREO', 1, 'U', 'A', '', 1095, 0, ''),
('dinghy_base', '329', 'RS VISION', 2, 'S', 'A', '', 1150, 5, ''),
('dinghy_base', '301', 'RS100 8.4', 1, 'U', 'A', '', 1002, 1, ''),
('dinghy_base', '303', 'RS200', 2, 'S', 'A', '', 1053, 3, ''),
('dinghy_base', '304', 'RS300', 1, 'U', '0', '', 965, 0, ''),
('dinghy_base', '305', 'RS400', 2, 'S', 'A', '', 945, 3, ''),
('dinghy_base', '306', 'RS500', 2, 'S', 'A', '', 963, 0, ''),
('dinghy_base', '307', 'RS600', 1, 'U', '0', '', 921, 0, ''),
('dinghy_base', '309', 'RS700', 1, 'U', 'A', '', 845, 0, ''),
('dinghy_base', '310', 'RS800', 2, 'S', 'A', '', 797, -2, ''),
('dinghy_base', '334', 'SCORPION', 2, 'S', 'C', '', 1042, 0, ''),
('dinghy_base', '335', 'SEAFLY', 2, 'S', 'C', '', 1074, -3, ''),
('dinghy_base', '348', 'SNIPE', 2, 'S', '0', '', 1104, -6, ''),
('dinghy_base', '350', 'SOLO', 1, 'U', '0', '', 1139, 0, ''),
('dinghy_base', '351', 'SOLUTION', 1, 'U', '0', '', 1112, 4, ''),
('dinghy_base', '355', 'SPLASH', 1, 'U', '0', '', 1247, 0, ''),
('dinghy_base', '363', 'STREAKER', 1, 'U', '0', '', 1121, -3, ''),
('dinghy_base', '367', 'SUPERNOVA', 1, 'U', '0', '', 1075, 0, ''),
('dinghy_base', '370', 'TASAR', 2, 'S', '0', '', 1022, 3, ''),
('dinghy_base', '379', 'TOPPER', 1, 'U', '0', '', 1369, 6, ''),
('dinghy_base', '380', 'TOPPER 4.2', 1, 'U', '0', '', 1450, 10, ''),
('dinghy_base', '411', 'WANDERER', 2, 'S', 'C', '', 1201, 0, ''),
('dinghy_base', '415', 'WAYFARER', 2, 'S', 'C', '', 1107, -2, ''),
('multihull_base', '19', 'A CLASS (NON-FOILING)', 1, 'U', '0', 'NON-FOILING', 695, 0, 'CLUBS TO DISTINGUISH BETWEEN FOILING AND NON-FOILING'),
('multihull_base', '55', 'CATAPULT', 1, 'U', '0', '', 898, 0, ''),
('multihull_base', '56', 'CHALLENGER', 1, 'U', '0', '', 1175, 4, ''),
('multihull_base', '84', 'DART 15 / SPRINT 15', 1, 'U', '0', '', 916, -8, ''),
('multihull_base', '86', 'DART 15 SPORT / SPRINT 15 SPORT', 1, 'S', '0', '', 904, 0, ''),
('multihull_base', '95', 'DART 18', 2, 'S', '0', '', 795, -15, ''),
('multihull_base', '187', 'HURRICANE 5.9 SX', 2, 'S', 'A', '', 680, -11, ''),
('multihull_base', '354', 'SPITFIRE', 1, 'U', 'A', '', 745, 5, ''),
('experimental', '36', 'BLAZE FIRE', 1, 'U', '0', '', 1050, 0, ''),
('experimental', '49', 'BYTE CI', 1, 'U', '0', '', 1223, 6, 'CLUBS TO DISTINGUISH BETWEEN CI AND CII'),
('experimental', '51', 'CADET', 2, 'S', 'C', '', 1455, 0, ''),
('experimental', '451', 'DEVOTI D ZERO - BLACK RIG', 1, 'U', '0', 'BLACK RIG', 1051, -6, ''),
('experimental', '151', 'FUSION PRO GEN', 2, 'S', 'A', '', 1275, 0, ''),
('experimental', '195', 'INTERNATIONAL CANOE', 1, 'S', '0', '', 858, 11, 'DEVELOPMENT CLASS'),
('experimental', '202', 'ISO', 2, 'S', 'A', '', 940, 12, ''),
('experimental', '507', 'MIRROR - NO SPINNAKER', 2, 'S', '0', 'NO SPINNAKER', 1376, 5, ''),
('experimental', '161', 'HANSA 303 - SINGLEHANDED', 1, 'U', '0', 'SINGLEHANDED', 1570, -10, ''),
('experimental', '162', 'HANSA LIBERTY', 1, 'U', '0', '', 1411, -12, ''),
('experimental', '553', 'HARTLEY ZENITH', 1, 'S', '0', '', 1051, 0, ''),
('experimental', '549', 'MELGES 15', 2, 'S', 'A', '', 994, 0, '')
) AS v(
    list_section, source_class_id, source_class_name, crew_count, rig, spinnaker,
    variant, rating_value, change_from_previous, source_notes
) ON TRUE
WHERE p.system_code = 'RYA_PY' AND p.version_label = '2026' AND p.version_number = '4'
AND NOT EXISTS (
    SELECT 1 FROM public.rating_catalogue_entry e
    WHERE e.publication_id = p.publication_id AND e.source_class_id = v.source_class_id
);

COMMIT;
