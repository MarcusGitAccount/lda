"""Demo document 5: a settlement agreement with a UK company (English)."""

from __future__ import annotations

from . import case as c
from .kit import Meta, PageBreak, article, clause, grid, p, plain_table, space, sub  # fmt: skip


def settlement():
    story = [
        p("DATED 18 JUNE 2025", "right"),
        space(1.2),
        p("SETTLEMENT AGREEMENT", "title"),
        p("relating to damaged cargo carried under CMR consignment note no. " + c.CMR_NO, "subtitle"),
        space(0.6),
        p(f"(1)  <b>{c.CLIENT_MIXED}</b>", "left"),
        p(f"(2)  <b>{c.UK}</b>", "left"),
        space(0.6),
        p("CONFIDENTIAL – SUBJECT TO THE TERMS OF CLAUSE 7", "subtitle"),
        PageBreak(),
        p("THIS AGREEMENT is dated 18 June 2025 and is made <b>BETWEEN</b>:"),
        clause("(1)", f"<b>{c.CLIENT_MIXED}</b>, a company incorporated in Romania with trade register number {c.CLIENT_REG} and tax identification number "
               f"RO{c.CLIENT_CUI}, whose registered office is at {c.CLIENT_STREET}, {c.CLIENT_CITY}, {c.CLIENT_POSTAL}, Romania (the <b>Exporter</b>); and"),
        clause("(2)", f"<b>{c.UK}</b>, a company incorporated in England and Wales with company number {c.UK_NUMBER}, whose registered office is at {c.UK_ADDR} "
               "(<b>Northgate</b>)."),
        p("The Exporter and Northgate are each a <b>party</b> and together the <b>parties</b>."),
        article("BACKGROUND"),
        clause("(A)", f"On 2 February 2025 Northgate collected 21 pallets of fresh blueberries (the <b>Goods</b>) from the Exporter's premises in {c.CLIENT_CITY} for carriage by road "
               f"to a customer of the Exporter in Manchester, United Kingdom, under CMR consignment note no. {c.CMR_NO} (the <b>Consignment Note</b>)."),
        clause("(B)", "The Goods arrived on 6 February 2025, 31 hours after the agreed delivery time. The consignee rejected the Goods because the temperature log "
               "showed that the temperature had been above 8°C for more than 19 hours."),
        clause("(C)", "The Exporter claimed £38,500 from Northgate for the value of the Goods and for related costs (the <b>Claim</b>). Northgate denied that it was "
               "liable for the whole of the Claim and referred to the limits of liability in Article 23 of the Convention on the Contract for the International Carriage "
               "of Goods by Road (the <b>CMR Convention</b>)."),
        clause("(D)", f"On 28 May 2025 the parties took part in a mediation in Leeds. {c.UK_DIRECTOR} attended for Northgate, advised by {c.UK_SOLICITOR} of "
               f"{c.UK_LAWFIRM}. {c.ADMIN} attended for the Exporter, advised by {c.LAWYER} of {c.FIRM}. The parties reached the agreement that this document records."),
        article("AGREED TERMS"),
        article("1.  Interpretation"),
        clause("1.1", "The definitions in this clause apply in this agreement. <b>Business Day</b>: a day other than a Saturday, a Sunday or a public holiday in England. "
               "<b>Effective Date</b>: the date of this agreement. <b>Settlement Sum</b>: £31,000 (thirty-one thousand pounds sterling)."),
        clause("1.2", "Clause headings do not affect the interpretation of this agreement. A reference to a clause or a Schedule is a reference to a clause of, or a Schedule "
               "to, this agreement. The Schedule forms part of this agreement."),
        article("2.  Settlement Sum"),
        clause("2.1", "Northgate shall pay the Settlement Sum to the Exporter within 14 days after the Effective Date, by transfer of cleared funds to the following account:"),
        grid(
            [
                ["Account holder", c.CLIENT_MIXED],
                ["Bank", "Banca Transilvania S.A."],
                ["IBAN", c.CLIENT_IBAN],
                ["SWIFT/BIC", "BTRLRO22"],
                ["Payment reference", f"Settlement {c.CMR_NO}"],
            ],
            [4.5, 11.5], header=False,
        ),
        space(0.3),
        clause("2.2", "Northgate shall make the payment in full without any set-off, counterclaim or deduction. If Northgate does not pay on time, it shall pay interest on "
               "the unpaid amount at 4% a year above the Bank of England base rate, from the due date until the date of payment."),
        clause("2.3", "The Exporter shall send a copy of the invoice for the Settlement Sum to " + f"{c.UK_EMAIL} within 5 Business Days after the Effective Date. "
               "A failure to send the invoice does not delay the payment."),
        article("3.  Release"),
        clause("3.1", "On receipt of the Settlement Sum in full, the Exporter releases Northgate, its insurers and its employees from all claims, known or unknown, that arise "
               "from or relate to the carriage of the Goods under the Consignment Note, including the Claim."),
        clause("3.2", "The release in clause 3.1 does not cover: "),
        sub("(a)", "Northgate's obligations under this agreement;"),
        sub("(b)", "any claim for fraud or fraudulent misrepresentation; or"),
        sub("(c)", "any claim that arises from another consignment, including the carriage that is the subject of the Exporter's separate dispute with a third party."),
        clause("3.3", "Northgate releases the Exporter from all claims that arise from or relate to the Consignment Note, including any claim for the carriage charges, which "
               "Northgate has already received."),
        article("4.  No admission"),
        clause("4.1", "This agreement is a compromise of a disputed claim. Neither party admits liability or wrongdoing, and neither party may use this agreement as evidence "
               "of liability in any other proceedings, except to enforce it."),
        article("5.  Costs"),
        clause("5.1", "Each party shall bear its own legal and other costs of the Claim and of the mediation. The parties shall share the mediator's fees equally."),
        article("6.  Warranties"),
        clause("6.1", "Each party warrants that it has the power and the authority to enter into and perform this agreement, and that the person who signs it for the party "
               "has been duly authorised to do so."),
        clause("6.2", "The Exporter warrants that it has not assigned any part of the Claim to another person."),
        article("7.  Confidentiality"),
        clause("7.1", "Each party shall keep the terms of this agreement, and the negotiations that led to it, confidential. A party may disclose them: (a) to its professional "
               "advisers, insurers and auditors, on a duty of confidence; (b) as the law, a court or a regulator requires; or (c) to the extent needed to enforce this agreement."),
        clause("7.2", "Each party shall comply with the data protection law that applies to it, including the UK GDPR and the Data Protection Act 2018, and Regulation (EU) "
               "2016/679, when it processes personal data under this agreement."),
        article("8.  Entire agreement and variation"),
        clause("8.1", "This agreement is the entire agreement between the parties about its subject matter. It replaces all earlier drafts, understandings and discussions, "
               "including the heads of terms that the parties signed at the mediation."),
        clause("8.2", "A variation of this agreement is valid only if it is in writing and signed by or for each party."),
        article("9.  Third party rights"),
        clause("9.1", "A person who is not a party to this agreement has no right under the Contracts (Rights of Third Parties) Act 1999 to enforce any of its terms, "
               "except that Northgate's insurers may enforce clause 3.1."),
        article("10.  Notices"),
        clause("10.1", "A notice under this agreement shall be in writing and sent by courier or by e-mail. The address of Northgate is " + f"{c.UK_ADDR}, "
               f"for the attention of {c.UK_DIRECTOR}, e-mail {c.UK_EMAIL}, telephone {c.UK_PHONE}. The address of the Exporter is {c.CLIENT_STREET}, "
               f"{c.CLIENT_CITY}, Romania, for the attention of {c.ADMIN}, e-mail {c.ADMIN_EMAIL}."),
        clause("10.2", "A notice sent by courier is received at 9.00 am on the second Business Day after posting. A notice sent by e-mail is received at the time of sending, "
               "or at 9.00 am on the next Business Day if the time of sending is outside business hours."),
        article("11.  Governing law and jurisdiction"),
        clause("11.1", "This agreement and any dispute or claim that arises out of or in connection with it are governed by the law of England and Wales."),
        clause("11.2", "The courts of England and Wales have exclusive jurisdiction to settle any such dispute or claim."),
        clause("11.3", f"Each party irrevocably agrees that {c.UK_LAWFIRM}, {c.UK_LAWFIRM_ADDR}, may accept service of any claim form for Northgate, and that the Exporter "
               f"shall appoint an agent in England for the same purpose within 30 days, if this agreement requires proceedings."),
        p("This agreement has been entered into on the date stated at the beginning of it."),
        space(0.3),
        plain_table(
            [
                [f"<b>Signed</b> by {c.ADMIN}, Administrator, for and on behalf of <b>{c.CLIENT_MIXED}</b>", ""],
                ["", "......................................................"],
                [f"In the presence of: {c.WITNESS}, interpreter", "......................................................"],
            ],
            [9.0, 7.0],
        ),
        space(0.6),
        plain_table(
            [
                [f"<b>Signed</b> by {c.UK_DIRECTOR}, Director, for and on behalf of <b>{c.UK}</b>", ""],
                ["", "......................................................"],
                [f"In the presence of: {c.UK_SOLICITOR}, solicitor", "......................................................"],
            ],
            [9.0, 7.0],
        ),
        PageBreak(),
        p("SCHEDULE", "title"),
        p("Consignment details", "subtitle"),
        grid(
            [
                ["Item", "Detail"],
                ["Consignment Note", c.CMR_NO],
                ["Date of collection", "2 February 2025"],
                ["Place of collection", f"{c.CLIENT_STREET}, {c.CLIENT_CITY}, Romania"],
                ["Place of delivery", "Manchester, United Kingdom"],
                ["Goods", "21 pallets of fresh blueberries, 6,300 kg"],
                ["Required temperature", "2°C to 4°C"],
                ["Agreed delivery time", "5 February 2025, 07:00"],
                ["Actual arrival", "6 February 2025, 14:00"],
                ["Invoice value of the Goods", "£31,200.00"],
                ["Claim", "£38,500.00"],
                ["Settlement Sum", "£31,000.00"],
            ],
            [5.5, 10.5],
        ),
        space(0.6),
        p(f"For payments from the United Kingdom, Northgate's own account, from which the payment is made, is {c.UK_IBAN}, held with Barclays Bank UK PLC.", "small"),
    ]
    meta = Meta(
        title="Settlement Agreement", author=c.UK_SOLICITOR, subject="Settlement agreement",
        header=f"Settlement Agreement – {c.CLIENT_MIXED} and {c.UK}",
        footer=f"Confidential  |  {c.UK_LAWFIRM}", page_label="Page {n} of {total}",
    )  # fmt: skip
    return story, meta
