"""Demo document 1: the transport contract (Romanian)."""

from __future__ import annotations

from . import case as c
from .kit import (
    Meta, PageBreak, article, clause, grid, letterhead, p, signatures, space, sub,
)  # fmt: skip


# --- 1. the contract -----------------------------------------------------------------


def contract():
    story = [
        *letterhead(
            f"S.C. {c.DEF}",
            [
                f"Sediul social: {c.DEF_ADDR}",
                f"Nr. Reg. Com.: {c.DEF_REG}  |  CUI: RO{c.DEF_CUI}  |  Capital social subscris și vărsat: 2.500.000 lei",
                f"Cont IBAN: {c.DEF_IBAN}  |  Tel.: {c.DEF_PHONE}  |  E-mail: {c.DEF_EMAIL}",
            ],
        ),
        p("CONTRACT DE PRESTĂRI SERVICII DE TRANSPORT RUTIER DE MARFĂ ȘI LOGISTICĂ", "title"),
        p("Nr. 128 din 22.03.2024", "subtitle"),
        p("Având în vedere dispozițiile Codului civil, ale Ordonanței Guvernului nr. 27/2011 privind transporturile rutiere și ale "
          "Convenției privind contractul de transport internațional rutier de mărfuri (Convenția CMR), s-a încheiat prezentul contract între:"),
        p(f"<b>1. S.C. {c.DEF}</b>, societate pe acțiuni de drept român, cu sediul social în {c.DEF_ADDR}, înregistrată la Oficiul Registrului "
          f"Comerțului de pe lângă Tribunalul Brașov sub nr. {c.DEF_REG}, cod unic de înregistrare RO{c.DEF_CUI}, cont IBAN {c.DEF_IBAN} deschis la "
          f"BRD – Groupe Société Générale S.A., reprezentată legal prin <b>{c.DEF_REP}</b>, în calitate de Director General, "
          "denumită în continuare <b>PRESTATOR</b>,"),
        p("și", "subtitle"),
        p(f"<b>2. S.C. {c.CLIENT}</b>, societate cu răspundere limitată de drept român, cu sediul social în {c.CLIENT_ADDR}, înregistrată la Oficiul "
          f"Registrului Comerțului de pe lângă Tribunalul Mureș sub nr. {c.CLIENT_REG}, cod unic de înregistrare RO{c.CLIENT_CUI}, cont IBAN "
          f"{c.CLIENT_IBAN} deschis la Banca Transilvania S.A., reprezentată legal prin <b>dl. {c.ADMIN}</b>, în calitate de Administrator, "
          f"identificat cu CNP {c.ADMIN_CNP}, denumită în continuare <b>BENEFICIAR</b>."),
        p("Prestatorul și Beneficiarul se numesc în mod individual „Partea” și în mod colectiv „Părțile”."),

        article("ARTICOLUL 1 – DEFINIȚII ȘI INTERPRETARE"),
        clause("1.1.", "În prezentul contract, termenii de mai jos au următoarea semnificație: <b>„Marfa”</b> – produsele agroalimentare proaspete sau refrigerate "
               "predate Prestatorului spre transport; <b>„Transport”</b> – deplasarea Mărfii între locul de încărcare și locul de descărcare indicate de Beneficiar "
               "în ordinul de transport; <b>„Ordin de transport”</b> – comanda scrisă transmisă de Beneficiar, care cuprinde cel puțin ruta, data și ora încărcării, "
               "temperatura de transport și destinatarul; <b>„Zi lucrătoare”</b> – orice zi, cu excepția sâmbetei, a duminicii și a zilelor de sărbătoare legală."),
        clause("1.2.", "Anexele fac parte integrantă din contract. În caz de contradicție între o anexă și corpul contractului, prevalează corpul contractului, "
               "cu excepția tarifelor, care se aplică așa cum sunt prevăzute în Anexa nr. 1."),
        clause("1.3.", "Titlurile articolelor sunt folosite doar pentru ușurința lecturii și nu influențează interpretarea clauzelor."),

        article("ARTICOLUL 2 – OBIECTUL CONTRACTULUI"),
        clause("2.1.", "Prestatorul se obligă să efectueze, în numele său și pe riscul său, transporturi rutiere de marfă la temperatură controlată, "
               "pentru Beneficiar, pe rutele și în condițiile stabilite prin Ordinele de transport, iar Beneficiarul se obligă să plătească prețul transporturilor."),
        clause("2.2.", "Prestatorul va asigura serviciile logistice conexe: preluarea Mărfii de la sediul Beneficiarului din " + f"{c.CLIENT_CITY}, {c.CLIENT_STREET}"
               ", verificarea la încărcare a stării Mărfii și a ambalajelor, monitorizarea temperaturii pe toată durata Transportului și predarea Mărfii destinatarului."),
        clause("2.3.", "Beneficiarul nu are obligația de a transmite Prestatorului un volum minim de comenzi. Părțile estimează, fără ca această estimare să "
               "constituie un angajament, un volum anual de aproximativ 2.400.000 lei, fără TVA."),

        article("ARTICOLUL 3 – DURATA CONTRACTULUI"),
        clause("3.1.", "Contractul intră în vigoare la data semnării de către ambele Părți și se încheie pe o durată de 24 de luni."),
        clause("3.2.", "Contractul se prelungește automat pentru perioade succesive de câte 12 luni, dacă niciuna dintre Părți nu notifică, cu cel puțin "
               "60 de zile înainte de expirare, intenția de a nu-l prelungi."),

        article("ARTICOLUL 4 – OBLIGAȚIILE PRESTATORULUI"),
        clause("4.1.", "Prestatorul se obligă:"),
        sub("a)", "să pună la dispoziție autovehicule izoterme sau frigorifice, în stare tehnică bună, cu inspecția tehnică periodică și cu certificatul "
            "de agreare pentru transportul produselor perisabile valabile pe toată durata contractului;"),
        sub("b)", "să mențină temperatura Mărfii în intervalul indicat în Ordinul de transport și să păstreze înregistrările înregistratorului de temperatură "
            "pe o perioadă de cel puțin 24 de luni;"),
        sub("c)", "să se prezinte la încărcare la data și la ora stabilite, cu o toleranță de cel mult 60 de minute;"),
        sub("d)", "să respecte termenele de livrare din Ordinul de transport și să informeze Beneficiarul, de îndată, despre orice eveniment care poate "
            "întârzia livrarea sau afecta Marfa;"),
        sub("e)", "să încheie și să mențină, pe toată durata contractului, o asigurare de răspundere civilă a transportatorului, cu o sumă asigurată de cel puțin "
            "1.000.000 lei pentru fiecare eveniment, și să transmită Beneficiarului o copie a poliței la cerere;"),
        sub("f)", "să utilizeze personal calificat și să respecte normele privind timpul de conducere și de odihnă."),
        clause("4.2.", f"Prestatorul desemnează ca persoană de contact pentru coordonarea operativă pe doamna {c.DISPATCHER}, dispecer, telefon {c.DISPATCHER_PHONE}, "
               f"e-mail {c.DISPATCHER_EMAIL}. Schimbarea persoanei de contact se comunică în scris, cu cel puțin 3 zile lucrătoare înainte."),

        article("ARTICOLUL 5 – OBLIGAȚIILE BENEFICIARULUI"),
        clause("5.1.", "Beneficiarul se obligă:"),
        sub("a)", "să transmită Ordinele de transport cu cel puțin 24 de ore înainte de data încărcării;"),
        sub("b)", "să predea Marfa ambalată și etichetată corespunzător și să furnizeze toate documentele necesare transportului;"),
        sub("c)", "să indice în Ordinul de transport temperatura de transport și orice cerință specială de manipulare;"),
        sub("d)", "să plătească prețul serviciilor la termenele prevăzute la Articolul 6."),
        clause("5.2.", f"Beneficiarul desemnează ca persoană de contact pe dl. {c.ADMIN}, telefon {c.ADMIN_PHONE}, e-mail {c.ADMIN_EMAIL}."),

        article("ARTICOLUL 6 – TARIFE, FACTURARE ȘI PLATĂ"),
        clause("6.1.", "Tarifele aplicabile sunt cele din Anexa nr. 1 și sunt exprimate în lei, fără TVA. Tarifele se pot modifica doar prin act adițional "
               "semnat de ambele Părți."),
        clause("6.2.", "Prestatorul emite factura după fiecare Transport finalizat, în termen de 5 zile lucrătoare de la data predării Mărfii, și o transmite "
               f"la adresa de e-mail {c.CLIENT_EMAIL}. Factura va cuprinde numărul Ordinului de transport și copia documentului de transport semnat de destinatar."),
        clause("6.3.", "Beneficiarul plătește factura în termen de 30 de zile de la data primirii ei, prin ordin de plată, în contul indicat de Prestator în "
               "preambul. Data plății este data la care suma intră în contul Prestatorului."),
        clause("6.4.", "Dacă Beneficiarul contestă în scris, motivat, o parte a facturii în termen de 10 zile de la primire, el plătește partea necontestată la "
               "scadență, iar Părțile încearcă să soluționeze diferența în termen de 15 zile."),
        clause("6.5.", "Pentru întârzierea la plată se datorează dobânda legală penalizatoare prevăzută de Ordonanța Guvernului nr. 13/2011, în condițiile Legii nr. 72/2013."),

        article("ARTICOLUL 7 – CONDIȚII DE TRANSPORT"),
        clause("7.1.", "Prestatorul preia Marfa pe baza scrisorii de transport și a procesului-verbal de predare-primire, semnate de reprezentanții ambelor Părți. "
               "Orice rezervă privind starea Mărfii se menționează în aceste documente."),
        clause("7.2.", "Autovehiculul trebuie să fie echipat cu un sistem de poziționare prin satelit și cu un înregistrator de temperatură calibrat. Prestatorul "
               "permite Beneficiarului accesul, în timp real, la datele de poziție și de temperatură prin platforma sa online."),
        clause("7.3.", "Dacă temperatura Mărfii depășește intervalul indicat în Ordinul de transport mai mult de 30 de minute consecutive, Prestatorul informează "
               "imediat Beneficiarul și execută instrucțiunile acestuia. Absența instrucțiunilor nu îl scutește pe Prestator de obligația de a lua toate măsurile "
               "rezonabile pentru a limita pierderea."),
        clause("7.4.", "Pentru transporturile internaționale se aplică și dispozițiile Convenției CMR, în măsura în care nu contravin prezentului contract."),

        article("ARTICOLUL 8 – RĂSPUNDEREA PENTRU MARFĂ"),
        clause("8.1.", "Prestatorul răspunde pentru pierderea totală sau parțială, avarierea și deteriorarea Mărfii, de la preluarea ei și până la predarea către "
               "destinatar, dacă nu dovedește că prejudiciul a fost cauzat de culpa Beneficiarului, de un viciu propriu al Mărfii sau de forța majoră."),
        clause("8.2.", "Despăgubirea se calculează la valoarea Mărfii la locul și la data preluării, așa cum rezultă din factura Beneficiarului, la care se "
               "adaugă costurile de transport, vamale și alte cheltuieli făcute în legătură cu Transportul."),
        clause("8.3.", "Dacă un prejudiciu este cauzat prin dol sau prin culpă gravă a Prestatorului ori a persoanelor pentru care acesta răspunde, "
               "limitările de răspundere din prezentul articol nu se aplică."),
        clause("8.4.", "Beneficiarul notifică Prestatorul despre orice lipsă sau avarie în termen de 48 de ore de la data la care a aflat de ea. Notificarea se "
               "transmite la adresa de e-mail a persoanei de contact și se confirmă prin scrisoare recomandată."),

        article("ARTICOLUL 9 – PENALITĂȚI"),
        clause("9.1.", "Pentru neplata facturii la scadență, Beneficiarul datorează penalități de 0,03% pe zi de întârziere, calculate la suma neachitată, "
               "fără ca totalul să depășească valoarea facturii."),
        clause("9.2.", "Pentru întârzierea livrării față de termenul din Ordinul de transport, Prestatorul datorează penalități de 0,5% pe zi de întârziere, "
               "calculate la valoarea Mărfii transportate, fără ca totalul să depășească 20% din această valoare. Pentru o fracțiune de zi se calculează o zi întreagă. "
               "Penalitățile se datorează de drept, fără punere în întârziere."),
        clause("9.3.", "Plata penalităților nu înlătură dreptul părții prejudiciate de a cere despăgubiri pentru partea din prejudiciu care depășește "
               "valoarea penalităților, în condițiile art. 1.530 și art. 1.531 din Codul civil."),

        article("ARTICOLUL 10 – FORȚA MAJORĂ"),
        clause("10.1.", "Forța majoră este evenimentul extern, imprevizibil, absolut invincibil și inevitabil, care împiedică partea să-și execute obligațiile. "
               "Partea care o invocă o notifică în scris în cel mult 5 zile de la apariție și transmite un certificat emis de autoritatea competentă în cel mult 30 de zile."),
        clause("10.2.", "Dacă forța majoră durează mai mult de 60 de zile, oricare dintre Părți poate denunța contractul, fără despăgubiri, printr-o notificare scrisă."),
        clause("10.3.", "Defecțiunile tehnice ale autovehiculelor Prestatorului, inclusiv ale instalației frigorifice, nu constituie forță majoră."),

        article("ARTICOLUL 11 – CONFIDENȚIALITATE ȘI PROTECȚIA DATELOR"),
        clause("11.1.", "Părțile păstrează confidențialitatea condițiilor contractului, a tarifelor și a oricărei informații comerciale primite de la cealaltă Parte, "
               "pe durata contractului și timp de 3 ani după încetarea lui."),
        clause("11.2.", "Fiecare Parte prelucrează datele cu caracter personal ale reprezentanților și ale angajaților celeilalte Părți, în calitate de operator "
               "independent, numai pentru executarea contractului și cu respectarea Regulamentului (UE) 2016/679 (GDPR)."),

        article("ARTICOLUL 12 – ÎNCETAREA CONTRACTULUI"),
        clause("12.1.", "Contractul încetează prin ajungere la termen, prin acordul Părților sau prin reziliere."),
        clause("12.2.", "Beneficiarul poate rezilia contractul, de drept, fără intervenția instanței, printr-o notificare scrisă, dacă Prestatorul întârzie "
               "livrarea în mai mult de 5 transporturi într-o perioadă de 6 luni sau dacă nu își reînnoiește asigurarea prevăzută la art. 4.1 lit. e), după "
               "un termen de grație de 10 zile acordat prin notificare."),
        clause("12.3.", "Prestatorul poate rezilia contractul în condițiile art. 12.2, dacă Beneficiarul nu plătește facturile scadente mai mult de 60 de zile, după "
               "punerea în întârziere printr-o notificare cu termen de 10 zile."),
        clause("12.4.", "Încetarea contractului nu afectează obligațiile născute înainte de data încetării, în special obligațiile de plată, de despăgubire și de "
               "confidențialitate."),

        article("ARTICOLUL 13 – NOTIFICĂRI"),
        clause("13.1.", "Orice notificare se face în scris și se transmite prin scrisoare recomandată cu confirmare de primire, prin curier cu confirmare sau prin "
               "e-mail, la adresele din preambul. Notificarea prin e-mail este valabilă dacă este confirmată în scris de destinatar sau dacă a fost însoțită de o copie "
               "transmisă prin curier."),
        clause("13.2.", "Notificarea se consideră primită la data confirmării de primire sau, în lipsa ei, în a treia zi lucrătoare de la expediere."),

        article("ARTICOLUL 14 – LEGEA APLICABILĂ ȘI SOLUȚIONAREA LITIGIILOR"),
        clause("14.1.", "Contractul este supus legii române."),
        clause("14.2.", f"Litigiile născute din sau în legătură cu contractul se soluționează pe cale amiabilă. Dacă nu se ajunge la un acord în 30 de zile, "
               f"litigiul se soluționează de instanțele competente din municipiul {c.CLIENT_CITY}, potrivit art. 126 din Codul de procedură civilă."),

        article("ARTICOLUL 15 – DISPOZIȚII FINALE"),
        clause("15.1.", "Modificarea contractului se face numai prin act adițional semnat de ambele Părți."),
        clause("15.2.", "Dacă o clauză este nulă sau inaplicabilă, celelalte clauze rămân valabile, iar Părțile o înlocuiesc cu o clauză valabilă, "
               "cu un efect economic apropiat."),
        clause("15.3.", "Prezentul contract s-a încheiat în două exemplare originale, câte unul pentru fiecare Parte, și cuprinde 2 anexe."),
        signatures(
            ["<b>PRESTATOR,</b>", f"S.C. {c.DEF}", "", "Director General,", f"<b>{c.DEF_REP}</b>"],
            ["<b>BENEFICIAR,</b>", f"S.C. {c.CLIENT}", "", "Administrator,", f"<b>{c.ADMIN}</b>"],
        ),
        PageBreak(),
        p("ANEXA NR. 1 la Contractul nr. 128 din 22.03.2024", "title"),
        p("TARIFE PENTRU TRANSPORT (lei, fără TVA)", "subtitle"),
        grid(
            [
                ["Ruta", "Tip vehicul", "Tarif / cursă", "Termen livrare"],
                [f"{c.CLIENT_CITY} – Brașov", "Autoizotermă 24 t", "3.150,00", "Aceeași zi"],
                [f"{c.CLIENT_CITY} – Cluj-Napoca", "Autoizotermă 24 t", "2.390,00", "Aceeași zi"],
                [f"{c.CLIENT_CITY} – Sibiu", "Autoizotermă 24 t", "2.050,00", "Aceeași zi"],
                [f"{c.CLIENT_CITY} – București", "Autofrigorifică 24 t", "5.480,00", "A doua zi, ora 06:00"],
                [f"{c.CLIENT_CITY} – Timișoara", "Autofrigorifică 24 t", "4.260,00", "A doua zi, ora 06:00"],
                ["Timp de așteptare peste 2 ore", "—", "180,00 / oră", "—"],
            ],
            [5.0, 4.0, 3.0, 4.0],
            right_cols=(2,),
        ),
        space(0.6),
        p("ANEXA NR. 2 la Contractul nr. 128 din 22.03.2024", "title"),
        p("PERSOANE DE CONTACT ȘI DATE DE FACTURARE", "subtitle"),
        grid(
            [
                ["", "Prestator", "Beneficiar"],
                ["Denumire", c.DEF_MIXED, c.CLIENT_MIXED],
                ["Cod unic de înregistrare", f"RO{c.DEF_CUI}", f"RO{c.CLIENT_CUI}"],
                ["Persoană de contact", c.DISPATCHER, c.ADMIN],
                ["Telefon", c.DISPATCHER_PHONE, c.ADMIN_PHONE],
                ["E-mail", c.DISPATCHER_EMAIL, c.ADMIN_EMAIL],
                ["E-mail pentru facturi", c.DEF_EMAIL, c.CLIENT_EMAIL],
            ],
            [4.2, 5.9, 5.9],
        ),
    ]
    meta = Meta(
        title="Contract de prestări servicii de transport nr. 128/2024", author=c.DEF_REP, subject="Contract",
        header=f"Contract nr. 128/22.03.2024 – {c.DEF_MIXED} / {c.CLIENT_MIXED}",
        footer=f"{c.DEF_MIXED} – CUI RO{c.DEF_CUI}",
    )  # fmt: skip
    return story, meta
