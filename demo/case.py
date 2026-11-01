"""The made-up case for the demo.

A Romanian farm exporter (the client of a law firm) sues its transport company
for spoiled goods and late deliveries. It also settles a claim with a UK freight
forwarder. All people and companies are fictional. The numbers have valid
checksums but they do not belong to real people or companies. E-mail addresses
use the reserved ".example" domain. UK phone numbers are in the range that
Ofcom keeps for television drama.
"""

from __future__ import annotations

from tests.samples import make_cnp, make_cui, make_iban

# --- the client ---------------------------------------------------------------
CLIENT = "MUREȘUL AGRO TRANS S.R.L."
CLIENT_MIXED = "Mureșul Agro Trans S.R.L."
CLIENT_SHORT = "Mureșul Agro Trans"
CLIENT_CUI = make_cui("3829174")
CLIENT_REG = "J26/1043/2012"
CLIENT_STREET = "str. Livezeni nr. 112"
CLIENT_CITY = "Târgu Mureș"
CLIENT_POSTAL = "540471"
CLIENT_ADDR = f"{CLIENT_CITY}, {CLIENT_STREET}, cod poștal {CLIENT_POSTAL}, jud. Mureș"
CLIENT_IBAN = make_iban("RO", "BTRL" + "RONCRT0381726405")
CLIENT_PHONE = "0265 411 902"
CLIENT_EMAIL = "office@agrotrans-mures.example"

ADMIN = "Cristian-Mihai Bălan"
ADMIN_REVERSED = "BĂLAN CRISTIAN-MIHAI"
ADMIN_CNP = make_cnp("181092226117")
ADMIN_ID_SERIES, ADMIN_ID_NO = "MS", "482615"
ADMIN_STREET = "str. Dózsa György nr. 14, ap. 9"
ADMIN_PHONE = "0744 620 315"
ADMIN_EMAIL = "c.balan@agrotrans-mures.example"

# --- the transport company (the other side) -------------------------------------
DEF = "CARPATICA LOGISTIC SOLUTIONS S.A."
DEF_MIXED = "Carpatica Logistic Solutions S.A."
DEF_SHORT = "Carpatica Logistic Solutions"
DEF_CUI = make_cui("4521937")
DEF_REG = "J08/2260/2009"
DEF_STREET = "Calea București nr. 87"
DEF_CITY = "Brașov"
DEF_POSTAL = "500123"
DEF_ADDR = f"{DEF_CITY}, {DEF_STREET}, cod poștal {DEF_POSTAL}, jud. Brașov"
DEF_IBAN = make_iban("RO", "BRDE" + "260SV31947182000")
DEF_PHONE = "0268 552 310"
DEF_EMAIL = "office@carpatica-logistic.example"

DEF_REP = "Gabriel-Tudor Lazăr"
DISPATCHER = "Ramona Ciobanu"
DISPATCHER_PHONE = "0741 330 218"
DISPATCHER_EMAIL = "r.ciobanu@carpatica-logistic.example"
DRIVER = "Marius Ghiță"

# the carrier that did the substitute transport
SUBST = "Someș Frig Trans S.R.L."
SUBST_SHORT = "Someș Frig Trans"

# the buyer of the goods
BUYER = "FreshMart Distribuție S.R.L."
BUYER_SHORT = "FreshMart Distribuție"
BUYER_MANAGER = "Daniela Florescu"

# --- the law firm ---------------------------------------------------------------
FIRM = "Societatea Civilă de Avocați Rusu și Asociații"
FIRM_SHORT = "Rusu și Asociații"
FIRM_STREET = "Piața Trandafirilor nr. 9, et. 2"
FIRM_ADDR = f"{CLIENT_CITY}, {FIRM_STREET}, jud. Mureș"
FIRM_CIF = make_cui("3517284")
FIRM_IBAN = make_iban("RO", "RNCB" + "0132007351284096")
FIRM_PHONE = "0265 218 640"
LAWYER = "Anca-Maria Rusu"
LAWYER_EMAIL = "anca.rusu@rusu-asociatii.example"
LAWYER2 = "Tudor Pașca"

# --- the court --------------------------------------------------------------------
COURT = "Tribunalul Mureș"
CASE_NO = "2871/102/2025"

# --- the UK side (English documents) ---------------------------------------------
UK = "Northgate Freight Forwarding Ltd"
UK_NUMBER = "09876543"
UK_ADDR = "Unit 4, Kingsway Business Park, Leeds LS11 9AQ"
UK_DIRECTOR = "Margaret Ellison"
UK_EMAIL = "m.ellison@northgate-freight.example"
UK_PHONE = "+44 113 496 0172"
UK_IBAN = make_iban("GB", "BARC20456173914826")
UK_SOLICITOR = "James R. Whitcombe"
UK_LAWFIRM = "Whitcombe Hale LLP"
UK_LAWFIRM_ADDR = "12 Park Row, Leeds LS1 5HD"
WITNESS = "Priya Raman"
CMR_NO = "RO-2025-0417"

# The 17 late deliveries: (date, destination, value of the goods in lei, delay in minutes).
# The penalty is 0.5% of the value of the goods for each day of delay (a part of a day counts as a day).
_LATE = [
    ("05.08.2024", "Brașov", 268_400, 15 * 60 + 30),
    ("19.08.2024", "Cluj-Napoca", 142_900, 9 * 60 + 15),
    ("02.09.2024", "București", 305_750, 11 * 60),
    ("30.09.2024", "Sibiu", 188_200, 7 * 60 + 40),
    ("14.10.2024", "Brașov", 251_300, 10 * 60 + 5),
    ("23.10.2024", "București", 330_600, 8 * 60 + 10),
    ("06.11.2024", "Timișoara", 297_800, 12 * 60 + 50),
    ("20.11.2024", "Cluj-Napoca", 156_450, 9 * 60 + 35),
    ("28.11.2024", "Brașov", 274_900, 14 * 60 + 20),
    ("12.12.2024", "Cluj-Napoca", 169_300, 16 * 60 + 45),
    ("19.12.2024", "București", 171_050, 27 * 60 + 10),
    ("09.01.2025", "Sibiu", 201_750, 8 * 60 + 55),
    ("16.01.2025", "Timișoara", 288_650, 13 * 60 + 40),
    ("23.01.2025", "Brașov", 263_500, 11 * 60 + 25),
    ("30.01.2025", "Sibiu", 192_400, 16 * 60 + 20),
    ("06.02.2025", "București", 318_900, 10 * 60 + 30),
    ("14.02.2025", "Timișoara", None, 13 * 60 + 5),  # the last value makes the total exact
]
PENALTIES = 21_438.00


def _days(minutes: int) -> int:
    return -(-minutes // (24 * 60))


def _build_delays():
    rows, so_far = [], 0.0
    for date, city, value, minutes in _LATE[:-1]:
        penalty = round(value * 0.005 * _days(minutes), 2)
        rows.append((date, city, value, minutes, _days(minutes), penalty))
        so_far += penalty
    date, city, _, minutes = _LATE[-1]
    days = _days(minutes)
    penalty = round(PENALTIES - so_far, 2)
    value = round(penalty / 0.005 / days)
    assert abs(value * 0.005 * days - penalty) < 0.005, (value, penalty)
    rows.append((date, city, value, minutes, days, penalty))
    return rows


DELAYS = _build_delays()
GOODS_KG = 19_800
GOODS_KG_TEXT = "19.800"
GOODS_PRICE = 24.50  # lei per kg of blueberries
GOODS_VALUE = GOODS_KG * GOODS_PRICE  # 485,100.00
LOST_MONTHS, LOST_PER_MONTH = 10, 39_100.00

# Amounts of the claim (lei). The sum is checked in `build.py`.
DAMAGES = [
    ("Marfă deteriorată (transport din 17.09.2024)", GOODS_VALUE),
    ("Penalități de întârziere (art. 9.2 din contract)", PENALTIES),
    ("Cost al transportului substitutiv", 96_470.00),
    ("Venit nerealizat (contractul cu rețeaua de retail)", LOST_MONTHS * LOST_PER_MONTH),
]
TOTAL = sum(amount for _, amount in DAMAGES)


def hours(minutes: int) -> str:
    return f"{minutes // 60} h {minutes % 60:02d} min"


def lei(amount: float) -> str:
    """Romanian number format: 1.184.500,00"""
    whole, cents = f"{amount:,.2f}".split(".")
    return f"{whole.replace(',', '.')},{cents}"


# Strings that must not stay in any hidden document. Each one is written in at
# least one document exactly like this.
MUST_HIDE = [
    CLIENT_SHORT, CLIENT_CUI, CLIENT_REG, CLIENT_STREET, CLIENT_POSTAL, CLIENT_IBAN, CLIENT_PHONE, CLIENT_EMAIL,
    ADMIN, "BĂLAN", ADMIN_CNP, f"{ADMIN_ID_SERIES} nr. {ADMIN_ID_NO}", ADMIN_STREET, ADMIN_PHONE, ADMIN_EMAIL,
    DEF_SHORT, DEF_CUI, DEF_REG, DEF_STREET, DEF_POSTAL, DEF_IBAN, DEF_PHONE, DEF_EMAIL,
    DEF_REP, DISPATCHER, DISPATCHER_PHONE, DISPATCHER_EMAIL, DRIVER, BUYER_SHORT, BUYER_MANAGER, SUBST_SHORT,
    FIRM_SHORT, FIRM_STREET, FIRM_CIF, FIRM_IBAN, FIRM_PHONE, LAWYER, LAWYER_EMAIL, LAWYER2,
    CASE_NO,
    UK, "Northgate", UK_NUMBER, "Kingsway Business Park", "LS11 9AQ", UK_DIRECTOR, UK_EMAIL, UK_PHONE, UK_IBAN,
    UK_SOLICITOR, UK_LAWFIRM, "12 Park Row", WITNESS, CMR_NO,
    "Târgu Mureș", "Brașov", "Leeds",
]  # fmt: skip

# Courts stay visible (the config says `keep_public_bodies: true`). The check does not count them.
VISIBLE_OK = ["Tribunalul Mureș", "Tribunalul Brașov"]

# Words that the reader needs and that are not private.
MUST_KEEP = [
    "PRESTATOR", "BENEFICIAR", "Reclamanta", "Pârâta", "Codul civil", "art. 1.350", "art. 1.530",
    "Convenția CMR", "GDPR", "Governing law", "England and Wales", "lei",
]  # fmt: skip
