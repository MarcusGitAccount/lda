"""Demo documents 2 to 4: documents of the law firm (Romanian).

A notice to the other side, the court claim, and the engagement contract with the client.
"""

from __future__ import annotations

from . import case as c
from .kit import Meta, PageBreak, article, clause, grid, letterhead, p, plain_table, signatures, space, sub  # fmt: skip


def firm_letterhead() -> list:
    return letterhead(
        c.FIRM,
        [
            f"Sediul profesional: {c.FIRM_ADDR}",
            f"Baroul Mureș  |  CIF: RO{c.FIRM_CIF}  |  Cont IBAN: {c.FIRM_IBAN}",
            f"Tel.: {c.FIRM_PHONE}  |  E-mail: {c.LAWYER_EMAIL}",
        ],
    )


def delay_table(rows, *, total: bool = True):
    data = [["Nr.", "Data", "Destinația", "Valoarea mărfii (lei)", "Întârziere", "Zile", "Penalitate (lei)"]]
    for number, (date, city, value, minutes, days, penalty) in enumerate(rows, 1):
        data.append([str(number), date, city, c.lei(value), c.hours(minutes), str(days), c.lei(penalty)])
    if total:
        data.append(["", "", "Total", "", "", "", c.lei(c.PENALTIES)])
    return grid(data, [1.0, 2.2, 2.9, 3.4, 2.5, 1.2, 2.8], right_cols=(3, 6), bold_last=total)


# --- 2. the notice -------------------------------------------------------------------


def notice():
    delays = delay_table([c.DELAYS[i] for i in (0, 5, 9, 14, 16)], total=False)
    story = [
        *firm_letterhead(),
        plain_table([["Nr. 214 din 10.03.2025", ""]], [8, 8]),
        space(0.3),
        plain_table(
            [
                ["<b>Către:</b>", f"S.C. {c.DEF}"],
                ["", f"{c.DEF_ADDR}"],
                ["<b>În atenția:</b>", f"dl. {c.DEF_REP}, Director General"],
                ["<b>Transmis prin:</b>", f"scrisoare recomandată cu confirmare de primire și e-mail, la {c.DEF_EMAIL}"],
            ],
            [3.2, 12.8],
        ),
        space(0.4),
        p("NOTIFICARE", "title"),
        p("punere în întârziere, somație de plată și preaviz de reziliere a Contractului nr. 128 din 22.03.2024", "subtitle"),
        p(f"Subsemnata <b>{c.LAWYER}</b>, avocat în {c.FIRM}, membră a Baroului Mureș, acționând în numele și pentru <b>S.C. {c.CLIENT}</b> "
          f"(denumită în continuare „Clientul nostru” sau „Beneficiarul”), pe baza împuternicirii avocațiale nr. 18/2025, vă comunic următoarele:"),
        article("1. Contractul"),
        p(f"Între societatea dumneavoastră, în calitate de prestator, și Clientul nostru, în calitate de beneficiar, s-a încheiat Contractul de prestări servicii "
          f"de transport rutier de marfă și logistică nr. 128 din 22.03.2024 („Contractul”). Clientul nostru este reprezentat de administratorul său, "
          f"dl. {c.ADMIN}. Contractul este în vigoare și a fost executat de Clientul nostru fără obiecții în ceea ce privește plata prețului."),
        article("2. Întârzieri repetate la livrare"),
        p("În perioada 05.08.2024 – 14.02.2025, societatea dumneavoastră a livrat cu întârziere în 17 transporturi. Prezentăm mai jos, cu titlu exemplificativ, "
          "cinci dintre ele. Lista completă, cu numerele ordinelor de transport, este în Anexa nr. 1 la prezenta notificare."),
        delays,
        space(0.3),
        p(f"Potrivit art. 9.2 din Contract, pentru fiecare zi de întârziere societatea dumneavoastră datorează penalități de 0,5% din valoarea mărfii transportate, "
          f"fără punere în întârziere. Penalitățile calculate pentru cele 17 transporturi sunt de <b>{c.lei(c.PENALTIES)} lei</b>."),
        article("3. Deteriorarea mărfii din 17.09.2024"),
        p(f"La data de 17.09.2024, în timpul transportului {c.CLIENT_CITY} – {c.DEF_CITY} al unei încărcături de 19.800 kg de afine proaspete, instalația frigorifică "
          f"a autovehiculului dumneavoastră s-a defectat. Șoferul, dl. {c.DRIVER}, a informat dispeceratul abia la ora 14:40, adică după aproximativ patru ore, "
          f"iar doamna {c.DISPATCHER} nu a transmis Clientului nostru nicio informare până la sosirea mărfii. Temperatura din semiremorcă a depășit 8°C timp de "
          f"peste șase ore. La sosire, reprezentanta destinatarului, doamna {c.BUYER_MANAGER} de la {c.BUYER}, a refuzat recepția și a întocmit procesul-verbal "
          f"de refuz din 18.09.2024. Marfa a fost distrusă. Valoarea ei, conform facturii Clientului nostru (19.800 kg × 24,50 lei/kg), este de <b>{c.lei(c.GOODS_VALUE)} lei</b>."),
        p("Prin aceste fapte au fost încălcate art. 4.1 lit. b) și d), art. 7.3 și art. 8.1 din Contract."),
        article("4. Pretenții și somație"),
        p("Vă punem în întârziere, în sensul art. 1.522 din Codul civil, și vă somăm să plătiți, în termen de <b>10 zile</b> de la primirea prezentei, "
          f"în contul IBAN {c.CLIENT_IBAN} deschis pe numele Clientului nostru, următoarele sume:"),
        sub("a)", f"{c.lei(c.PENALTIES)} lei, penalități de întârziere (art. 9.2 din Contract);"),
        sub("b)", f"{c.lei(c.GOODS_VALUE)} lei, contravaloarea mărfii deteriorate (art. 8.1 și art. 8.2 din Contract);"),
        sub("c)", "96.470,00 lei, costul transportului substitutiv comandat de Clientul nostru."),
        p("Clientul nostru își rezervă dreptul de a solicita și repararea prejudiciului constând în venitul nerealizat, în condițiile art. 1.530 și art. 1.531 "
          "din Codul civil, precum și dobânda legală penalizatoare."),
        article("5. Preaviz de reziliere"),
        p("Dacă nu plătiți sumele de mai sus în termenul de 10 zile, Contractul se consideră reziliat de drept, fără altă formalitate și fără intervenția "
          "instanței, în temeiul art. 12.2 din Contract și al art. 1.552 din Codul civil. Vom sesiza instanța competentă cu o cerere de chemare în judecată."),
        article("6. Păstrarea probelor"),
        p("Vă somăm să păstrați, până la finalul oricărui litigiu, înregistrările sistemului de poziționare și ale înregistratorului de temperatură pentru toate "
          "transporturile din perioada 22.03.2024 – 14.02.2025, precum și comunicările interne referitoare la ele."),
        p(f"Pentru lămuriri mă puteți contacta la {c.FIRM_PHONE} sau la {c.LAWYER_EMAIL}."),
        signatures(
            [f"{c.CLIENT_CITY}, 10.03.2025", ""],
            ["Avocat,", f"<b>{c.LAWYER}</b>"],
        ),
        p("Anexa nr. 1 – lista celor 17 transporturi livrate cu întârziere (în continuare).", "small"),
        p("Anexa nr. 2 – procesul-verbal de refuz din 18.09.2024 și înregistrarea de temperatură.", "small"),
        PageBreak(),
        p("ANEXA NR. 1 la Notificarea nr. 214 din 10.03.2025", "title"),
        p("Transporturi livrate cu întârziere – calculul penalităților (art. 9.2 din Contract)", "subtitle"),
        delay_table(c.DELAYS),
        space(0.3),
        p("Penalitatea este de 0,5% din valoarea mărfii transportate pentru fiecare zi de întârziere; o fracțiune de zi se calculează ca o zi întreagă. "
          "Totalul penalităților nu depășește 20% din valoarea mărfii pentru niciun transport.", "small"),
    ]
    meta = Meta(
        title="Notificare nr. 214/2025", author=c.LAWYER, subject="Notificare",
        header=f"Notificare nr. 214/10.03.2025 – {c.FIRM_SHORT}", footer=f"{c.FIRM}, {c.CLIENT_CITY}",
    )  # fmt: skip
    return story, meta


# --- 3. the court claim -----------------------------------------------------------------


def claim():
    first, last = min(r[3] for r in c.DELAYS), max(r[3] for r in c.DELAYS)
    story = [
        p("<b>Către,</b>", "left"),
        p("<b>TRIBUNALUL MUREȘ</b> – Secția a II-a civilă", "left"),
        p(f"Dosar nr. {c.CASE_NO}  |  Înregistrat la 05.05.2025", "right"),
        space(0.2),
        p("Domnule Președinte,"),
        p(f"<b>Reclamantă:</b> S.C. {c.CLIENT}, cu sediul în {c.CLIENT_ADDR}, înregistrată la Oficiul Registrului Comerțului sub nr. {c.CLIENT_REG}, "
          f"cod unic de înregistrare RO{c.CLIENT_CUI}, reprezentată legal prin administrator {c.ADMIN}, prin avocat {c.LAWYER} din cadrul {c.FIRM}, "
          f"cu sediul profesional ales pentru comunicarea actelor de procedură în {c.FIRM_ADDR}, tel. {c.FIRM_PHONE}, e-mail {c.LAWYER_EMAIL}."),
        p(f"<b>Pârâtă:</b> S.C. {c.DEF}, cu sediul în {c.DEF_ADDR}, înregistrată la Oficiul Registrului Comerțului sub nr. {c.DEF_REG}, "
          f"cod unic de înregistrare RO{c.DEF_CUI}, reprezentată legal prin Director General {c.DEF_REP}."),
        p("În contradictoriu cu Pârâta, formulăm prezenta"),
        p("CERERE DE CHEMARE ÎN JUDECATĂ", "title"),
        p("prin care solicităm instanței ca, prin hotărârea ce o va pronunța, să dispună:"),
        sub("1.", f"obligarea Pârâtei la plata către Reclamantă a sumei de <b>{c.lei(c.TOTAL)} lei</b>, reprezentând despăgubiri pentru neexecutarea "
            "Contractului nr. 128 din 22.03.2024, detaliate în tabelul de mai jos;"),
        sub("2.", "obligarea Pârâtei la plata dobânzii legale penalizatoare, calculate de la data scadenței fiecărei sume și până la plata integrală;"),
        sub("3.", "obligarea Pârâtei la plata cheltuielilor de judecată, constând în taxa judiciară de timbru, onorariul de avocat și onorariul expertului."),
        grid(
            [["Capăt de cerere", "Suma (lei)"], *[[name, c.lei(amount)] for name, amount in c.DAMAGES], ["Total", c.lei(c.TOTAL)]],
            [12.0, 4.0], right_cols=(1,), bold_last=True,
        ),
        space(0.3),
        article("I. SITUAȚIA DE FAPT"),
        p("<b>A. Contractul.</b> La data de 22.03.2024, Reclamanta, în calitate de beneficiar, și Pârâta, în calitate de prestator, au încheiat Contractul de "
          "prestări servicii de transport rutier de marfă și logistică nr. 128 (Contractul), pentru transportul produselor agroalimentare proaspete la temperatură "
          "controlată, pe rutele din Anexa nr. 1 la Contract. Contractul are o durată de 24 de luni. Pârâta s-a obligat, prin art. 4.1, să folosească autovehicule "
          "frigorifice în stare bună, să mențină temperatura mărfii și să respecte termenele de livrare. Prin art. 7.3, Pârâta s-a obligat să informeze imediat "
          "Reclamanta dacă temperatura depășește intervalul din ordinul de transport."),
        p(f"<b>B. Întârzierile.</b> În perioada 05.08.2024 – 14.02.2025, Pârâta a livrat cu întârziere în 17 transporturi, cu întârzieri între {c.hours(first)} și "
          f"{c.hours(last)}. Reclamanta a plătit prețul tuturor transporturilor, fără rezerve. Pentru întârzieri, art. 9.2 din Contract prevede penalități de 0,5% pe zi, "
          f"calculate la valoarea mărfii transportate și datorate de drept. Calculul pentru fiecare transport este în Anexa nr. 1 la prezenta cerere. "
          f"Totalul penalităților este de {c.lei(c.PENALTIES)} lei."),
        p(f"<b>C. Incidentul din 17.09.2024.</b> În ziua de 17.09.2024, Pârâta a preluat de la sediul Reclamantei din {c.CLIENT_CITY} {c.GOODS_KG_TEXT} kg de afine proaspete, "
          f"pentru depozitul central al cumpărătorului, {c.BUYER}, din {c.DEF_CITY}. Pe traseu, instalația frigorifică a autovehiculului s-a defectat. "
          f"Șoferul Pârâtei, dl. {c.DRIVER}, a anunțat dispeceratul Pârâtei după aproximativ patru ore. Dispecera {c.DISPATCHER} nu a informat Reclamanta. "
          f"Temperatura a depășit 8°C timp de peste șase ore, față de intervalul de 2–4°C din ordinul de transport. La sosire, doamna {c.BUYER_MANAGER}, "
          "responsabil de recepție al cumpărătorului, a refuzat marfa și a întocmit procesul-verbal de refuz din 18.09.2024. Marfa a fost distrusă."),
        p(f"<b>D. Consecințele.</b> Pentru a-și îndeplini obligațiile față de cumpărător, Reclamanta a comandat, la 19.09.2024, două transporturi de înlocuire "
          f"de la {c.SUBST}, pentru care a plătit 96.470,00 lei. Cumpărătorul, {c.BUYER_SHORT}, a încetat apoi să mai comande de la Reclamantă. "
          "Contractul-cadru dintre ele, încheiat la 01.09.2023 pe 24 de luni, ar fi produs efecte până la 31.08.2025. Pentru cele 10 luni rămase, marja brută lunară "
          f"medie a Reclamantei din acest contract, de 39.100,00 lei, nu a mai fost realizată. Pierderea este de {c.lei(c.LOST_MONTHS * c.LOST_PER_MONTH)} lei."),
        p(f"<b>E. Încercarea de soluționare amiabilă.</b> Prin notificarea nr. 214 din 10.03.2025, Reclamanta a pus în întârziere Pârâta și i-a acordat un termen de "
          f"10 zile pentru plată. La 24.03.2025, dl. {c.DEF_REP} a răspuns prin e-mail că Pârâta „nu recunoaște nicio datorie”, fără să conteste faptele. "
          "Contractul a fost reziliat de drept la expirarea termenului din notificare."),
        article("II. MOTIVELE ÎN DREPT"),
        p("<b>1. Competența.</b> Tribunalul este competent material potrivit art. 95 pct. 1 din Codul de procedură civilă. Competența teritorială a fost stabilită "
          f"prin convenția părților din art. 14.2 din Contract, care trimite la instanțele din {c.CLIENT_CITY}, în condițiile art. 126 din același cod."),
        p("<b>2. Răspunderea contractuală.</b> Potrivit art. 1.270 din Codul civil, contractul valabil încheiat are putere de lege între părți. Neexecutarea "
          "obligațiilor angajează răspunderea contractuală a debitorului, conform art. 1.350 din Codul civil. Condițiile sunt îndeplinite: Pârâta nu și-a "
          "executat obligațiile (întârzieri, defectarea instalației, informarea tardivă), Reclamanta a suferit un prejudiciu, iar între ele există legătură de cauzalitate."),
        p("<b>3. Culpa.</b> Culpa Pârâtei se prezumă, potrivit art. 1.548 din Codul civil, iar Pârâta nu poate dovedi o cauză străină. Defecțiunea unei instalații "
          "frigorifice pe care Pârâta a pus-o la dispoziție nu este forță majoră în sensul art. 1.351 din Codul civil, iar art. 10.3 din Contract o exclude în mod expres."),
        p("<b>4. Întinderea prejudiciului.</b> Creditorul poate cere daune-interese pentru prejudiciul care este consecința directă a neexecutării (art. 1.530 din "
          "Codul civil), iar reparația cuprinde pierderea suferită și câștigul nerealizat (art. 1.531 din Codul civil). Prejudiciul era previzibil la data încheierii "
          "Contractului (art. 1.533 din Codul civil): Pârâta știa că transportă produse perisabile pentru un exportator care le livrează unor rețele de retail."),
        p("<b>5. Penalitățile.</b> Clauza din art. 9.2 din Contract este o clauză penală în sensul art. 1.538 din Codul civil. Penalitățile se datorează fără "
          "dovada prejudiciului și sancționează numai întârzierile. Despăgubirile pentru marfa distrusă, pentru transportul de înlocuire și pentru venitul nerealizat "
          "repară alte prejudicii, care nu se leagă de întârzieri, așa că nu există cumul pentru același prejudiciu, în sensul art. 9.3 din Contract."),
        p("<b>6. Dobânda.</b> Pentru sumele neplătite se datorează dobânda legală penalizatoare, potrivit art. 1.535 din Codul civil și Ordonanței "
          "Guvernului nr. 13/2011, în condițiile Legii nr. 72/2013."),
        p("<b>7. Cheltuielile de judecată</b> se cer în temeiul art. 451 și art. 453 din Codul de procedură civilă. Taxa judiciară de timbru se calculează potrivit "
          "Ordonanței de urgență a Guvernului nr. 80/2013 și a fost achitată, conform dovezii anexate."),
        article("III. CUANTUMUL PREJUDICIULUI"),
        sub("1.", f"<b>Marfa distrusă:</b> {c.GOODS_KG_TEXT} kg × 24,50 lei/kg = {c.lei(c.GOODS_VALUE)} lei, conform facturii Reclamantei seria MAT nr. 0417 din 16.09.2024."),
        sub("2.", f"<b>Penalități de întârziere:</b> {c.lei(c.PENALTIES)} lei, calculate pentru 17 transporturi, conform Anexei nr. 1."),
        sub("3.", f"<b>Transport de înlocuire:</b> 96.470,00 lei, conform facturilor emise de {c.SUBST_SHORT} din 19.09.2024 și 20.09.2024."),
        sub("4.", f"<b>Venit nerealizat:</b> {c.LOST_MONTHS} luni × {c.lei(c.LOST_PER_MONTH)} lei = {c.lei(c.LOST_MONTHS * c.LOST_PER_MONTH)} lei. Reclamanta cere instanței să "
            "încuviințeze o expertiză contabilă pentru confirmarea marjei brute lunare."),
        p(f"Total: <b>{c.lei(c.TOTAL)} lei</b>.", "left"),
        article("IV. PROBE"),
        p("Solicităm încuviințarea următoarelor probe:"),
        sub("a)", "înscrisuri: Contractul și anexele sale, ordinele de transport, facturile, scrisorile de transport, notificarea nr. 214/2025 și dovada "
            "comunicării, răspunsul din 24.03.2025, procesul-verbal de refuz din 18.09.2024, înregistrările de temperatură, contractul-cadru cu cumpărătorul;"),
        sub("b)", "obligarea Pârâtei să depună înregistrările sistemului de poziționare și ale înregistratorului de temperatură, conform art. 293 din Codul de procedură civilă;"),
        sub("c)", f"interogatoriul Pârâtei, prin reprezentantul său legal, dl. {c.DEF_REP};"),
        sub("d)", f"proba cu martorii {c.DRIVER}, {c.DISPATCHER} și {c.BUYER_MANAGER}, ale căror date de identificare le vom indica la termen;"),
        sub("e)", "expertiză tehnică în specialitatea transporturi rutiere de marfă la temperatură controlată și expertiză contabilă pentru calculul penalităților "
            "și al dobânzii."),
        article("V. ANEXE"),
        p("Dovada achitării taxei judiciare de timbru; împuternicirea avocațială nr. 18/2025; copiile înscrisurilor de la pct. IV lit. a); copii pentru Pârâtă."),
        p("Pentru aceste motive, vă rugăm să admiteți cererea așa cum a fost formulată. În temeiul art. 411 alin. (1) pct. 2 din Codul de procedură civilă, solicităm "
          "judecarea cauzei și în lipsa noastră."),
        signatures(
            [f"{c.CLIENT_CITY}, 05.05.2025", ""],
            ["Pentru Reclamantă,", f"Avocat <b>{c.LAWYER}</b>"],
        ),
        PageBreak(),
        p("ANEXA NR. 1 la cererea de chemare în judecată", "title"),
        p("Calculul penalităților de întârziere (art. 9.2 din Contractul nr. 128/2024)", "subtitle"),
        delay_table(c.DELAYS),
        space(0.3),
        p("Penalitatea este de 0,5% din valoarea mărfii transportate pentru fiecare zi de întârziere; o fracțiune de zi se calculează ca o zi întreagă.", "small"),
    ]
    meta = Meta(
        title="Cerere de chemare în judecată", author=c.LAWYER, subject=f"Dosar {c.CASE_NO}",
        header=f"Dosar nr. {c.CASE_NO} – Cerere de chemare în judecată – Reclamantă: {c.CLIENT_MIXED}",
        footer=f"{c.FIRM_SHORT}  |  {c.LAWYER}",
    )  # fmt: skip
    return story, meta


# --- 4. the engagement contract -----------------------------------------------------------


def engagement():
    story = [
        *firm_letterhead(),
        p("CONTRACT DE ASISTENȚĂ JURIDICĂ", "title"),
        p("Nr. 18 din 03.03.2025", "subtitle"),
        p("Între:"),
        p(f"<b>{c.FIRM}</b>, cu sediul profesional în {c.FIRM_ADDR}, cod de identificare fiscală RO{c.FIRM_CIF}, cont IBAN {c.FIRM_IBAN}, "
          f"reprezentată prin avocat {c.LAWYER}, denumită în continuare <b>CABINETUL</b>,"),
        p("și"),
        p(f"<b>S.C. {c.CLIENT}</b>, cu sediul în {c.CLIENT_ADDR}, cod unic de înregistrare RO{c.CLIENT_CUI}, reprezentată prin administrator "
          f"<b>{c.ADMIN}</b>, domiciliat în {c.CLIENT_CITY}, {c.ADMIN_STREET}, identificat cu CI seria {c.ADMIN_ID_SERIES} nr. {c.ADMIN_ID_NO}, CNP {c.ADMIN_CNP}, "
          f"telefon {c.ADMIN_PHONE}, e-mail {c.ADMIN_EMAIL}, denumită în continuare <b>CLIENTUL</b>."),
        article("1. Obiectul contractului"),
        clause("1.1.", "Cabinetul acordă Clientului asistență juridică și reprezentare în litigiul împotriva "
               f"S.C. {c.DEF}, pentru recuperarea prejudiciilor născute din neexecutarea Contractului de transport nr. 128/2024, inclusiv notificarea pârâtei, "
               "redactarea cererii de chemare în judecată, reprezentarea în fața Tribunalului Mureș și, la cerere, în căile de atac."),
        clause("1.2.", f"Asistența se acordă prin avocat {c.LAWYER}, cu sprijinul avocatului {c.LAWYER2}."),
        article("2. Onorariul"),
        clause("2.1.", "Onorariul fix este de <b>18.000 lei</b>, fără TVA, plătibil astfel: 50% la semnarea contractului și 50% la depunerea cererii de chemare în judecată."),
        clause("2.2.", "Onorariul de succes este de 3% din sumele încasate efectiv de Client de la Pârâtă, plătibil în 5 zile de la încasare."),
        clause("2.3.", f"Plata se face prin ordin de plată în contul {c.FIRM_IBAN}, pe baza facturii emise de Cabinet. Onorariul nu include taxele judiciare de timbru, "
               "onorariile experților și alte cheltuieli de judecată, pe care le suportă Clientul."),
        article("3. Obligațiile Cabinetului"),
        clause("3.1.", "Cabinetul acționează cu diligență profesională, în conformitate cu Legea nr. 51/1995 și cu Statutul profesiei de avocat, și informează "
               "Clientul periodic despre stadiul litigiului."),
        clause("3.2.", "Cabinetul păstrează secretul profesional în legătură cu toate informațiile primite de la Client, fără limită în timp."),
        article("4. Obligațiile Clientului"),
        clause("4.1.", "Clientul pune la dispoziție, la timp și complet, documentele și informațiile cerute de Cabinet, și îl informează despre orice fapt nou."),
        clause("4.2.", "Clientul nu negociază și nu încheie nicio înțelegere cu Pârâta fără a consulta Cabinetul."),
        article("5. Date cu caracter personal"),
        clause("5.1.", "Cabinetul prelucrează datele Clientului și ale reprezentanților săi numai pentru acordarea asistenței juridice, ca operator, potrivit "
               "Regulamentului (UE) 2016/679 (GDPR). Cabinetul poate folosi instrumente software de redactare asistată, numai după ce a ascuns datele de identificare ale "
               "Clientului și ale celorlalte persoane din documente."),
        article("6. Încetarea contractului"),
        clause("6.1.", "Oricare parte poate denunța contractul printr-o notificare scrisă. Clientul datorează onorariul pentru activitățile efectuate până la data denunțării."),
        clause("6.2.", "Litigiile privind onorariul se soluționează conform Statutului profesiei de avocat, iar în lipsa unei soluții amiabile, de instanța competentă."),
        signatures(
            ["<b>CABINETUL,</b>", f"{c.FIRM}", "", f"Avocat <b>{c.LAWYER}</b>"],
            ["<b>CLIENTUL,</b>", f"S.C. {c.CLIENT}", "", f"Administrator <b>{c.ADMIN}</b>"],
        ),
        PageBreak(),
        *firm_letterhead(),
        p("ÎMPUTERNICIRE AVOCAȚIALĂ", "title"),
        p("Nr. 18 din 03.03.2025", "subtitle"),
        p(f"Prin prezenta, {c.FIRM}, prin avocat {c.LAWYER}, este împuternicită să reprezinte și să asiste pe <b>S.C. {c.CLIENT}</b>, cu sediul în {c.CLIENT_ADDR}, "
          f"cod unic de înregistrare RO{c.CLIENT_CUI}, în litigiul cu <b>S.C. {c.DEF}</b>, având ca obiect pretenții, în fața Tribunalului Mureș și a oricărei alte "
          "instanțe sau autorități. Avocatul poate: să semneze și să depună cereri și înscrisuri, să propună probe, să primească actele de procedură, "
          "să exercite căile de atac și să încheie tranzacții numai cu acordul scris al mandantului."),
        p("Împuternicirea este valabilă până la finalizarea definitivă a litigiului, în condițiile Codului de procedură civilă."),
        signatures(
            [f"{c.CLIENT_CITY}, 03.03.2025", ""],
            ["Mandant,", f"Administrator <b>{c.ADMIN}</b>"],
        ),
    ]
    meta = Meta(
        title="Contract de asistență juridică nr. 18/2025", author=c.LAWYER, subject="Contract de asistență juridică",
        header=f"Contract de asistență juridică nr. 18/03.03.2025 – {c.FIRM_SHORT}", footer=f"{c.FIRM}, {c.CLIENT_CITY}",
    )  # fmt: skip
    return story, meta
