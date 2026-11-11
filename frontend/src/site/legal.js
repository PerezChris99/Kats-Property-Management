/*
  Informational policy drafts. These are NOT a substitute for legal review.
  A published, owner-approved backend LegalPage supersedes the corresponding
  draft on the public site. Do not invent a company address, support email,
  uptime guarantee, or regulatory certification.
*/
export const POLICY_PAGES = {
  privacy: {
    title: 'Privacy policy', updated: 'Draft for review · November 2026',
    intro: 'How KATS Property Management is designed to handle information supplied by operators, staff and tenants.',
    sections: [
      ['Who is responsible', 'KATS is a property-management software system. The property business operating your deployment determines which tenant, lease and payment records it collects and how it uses them. For questions about your records, contact that property business or use the access request form on this site. The operator must supply its registered legal identity and privacy contact before publishing a final policy.'],
      ['Information handled', 'The system may process names, contact details, property and room references, leases, rental invoices, payment confirmations, maintenance requests, support inquiries, access logs and security events. Document uploads may contain personal information. Operators should collect only what is necessary for legitimate property operations.'],
      ['Purposes', 'Information supports property and tenancy administration, rent accounting, service requests, access control, account recovery, auditability, support and any legal obligations that apply to the operator. Payment or fiscal integrations are available only when configured and approved by the operator.'],
      ['Access and protection', 'Access is role-based and checked on the server. Sensitive workflows require authenticated accounts. Operators are responsible for safe passwords, correct role assignments, backups, secure hosting and retention decisions. No security system can guarantee zero risk.'],
      ['Sharing and processors', 'Information may be processed by hosting providers and optional payment, messaging or storage services selected by the operator. No integrations should be assumed active without configuration. Transfers and disclosures must be assessed under applicable data protection law.'],
      ['Retention and rights', 'The operator should define retention periods appropriate to its business, statutory obligations and disputes. Individuals may request access, correction, deletion or other rights where applicable through the responsible property business. Administrative privacy-request tools support tracking those requests.'],
      ['Cookies and contact', 'Essential session and CSRF cookies help secure access. See the Cookie policy for more information. Use the site access request form to send an inquiry; do not include account passwords, government identifiers or financial card information in messages.']
    ]
  },
  terms: {
    title: 'Terms of service', updated: 'Draft for review · November 2026',
    intro: 'Conditions for access to a KATS deployment, subject to the operator’s signed agreement and final published terms.',
    sections: [
      ['Authorized access', 'Only users authorized by the property business may access its operational workspace. User accounts and roles are issued by that business. Users must keep credentials private and provide accurate records.'],
      ['Permitted use', 'Use the platform to manage property, tenancy, maintenance, rental and approved accounting activities. Do not bypass permissions, access other tenants’ information, falsify payments or interfere with service availability.'],
      ['Financial records', 'A payment shown in KATS may be a recorded transaction awaiting independent confirmation. Bank, cash, mobile-money and tax records require the operator’s verification procedures; software records alone do not establish receipt of funds or legal compliance.'],
      ['Availability and third parties', 'The operator determines availability, service levels, support, fees, backups and external providers under its agreement. No uptime, payment-processing, legal or tax outcome is guaranteed by this public summary.'],
      ['Intellectual property', 'KATS source code and interface assets are licensed and protected according to the applicable software license and deployment agreement. Access to the service does not transfer ownership.'],
      ['Suspension and disputes', 'The property business may suspend accounts for security or contractual reasons. Applicable contracts and law govern termination, data export, dispute handling, limitations of liability and governing jurisdiction.']
    ]
  },
  cookies: {
    title: 'Cookie policy', updated: 'Draft for review · November 2026',
    intro: 'A plain-language explanation of essential cookies used for authenticated sessions.',
    sections: [
      ['Essential session cookies', 'When you sign in, the backend may set secure access and refresh cookies, together with CSRF tokens that help protect account actions. These cookies are necessary for sign-in and are not used as marketing tracking cookies by the KATS application.'],
      ['Local preferences', 'The site may use transient browser state for interactive controls such as an open navigation menu or selected slideshow image. Essential app behavior does not require third-party tracking cookies.'],
      ['Third-party services', 'If the operator enables external analytics, chat, media or payment providers, additional disclosures and consent controls may be required before those services are used. They are not assumed to be enabled in the default application.'],
      ['Your choices', 'You can clear cookies through browser settings, although doing so may sign you out. Contact the operator regarding any deployment-specific cookie technologies beyond those described here.']
    ]
  },
  refund: {
    title: 'Billing and refunds', updated: 'Draft for review · November 2026',
    intro: 'Software subscription billing and rent payments are separate subjects.',
    sections: [
      ['Software subscriptions', 'KATS does not advertise a public self-service software subscription checkout on this site. Any licensing fees, cancellation terms, refund eligibility and notice periods must be stated in a signed service or commercial agreement with the operator.'],
      ['Rental payments', 'Rent and deposits are governed by the relevant tenancy contract and applicable law. They are not refundable merely because they are recorded in KATS. Reversing an accounting record does not automatically return money to a payer.'],
      ['Disputes', 'Send billing concerns to the property business managing your account, or submit an inquiry through the access request form for routing. Include transaction references only; never send passwords or payment card details.']
    ]
  },
  'data-protection': {
    title: 'Data protection and security', updated: 'Draft for review · November 2026',
    intro: 'Design safeguards and the responsibilities of deployment operators.',
    sections: [
      ['Role-based boundaries', 'KATS uses server-side authorization and per-role workspace views. Certain sensitive records rely on PostgreSQL-specific row-level security in full deployments; that protection is not provided by the SQLite development preview.'],
      ['Secrets and connections', 'Production environments require HTTPS, strong application secrets, secure session-cookie settings and properly restricted database credentials. External services must be configured and approved independently.'],
      ['Financial audit trails', 'Important accounting changes can be recorded with an audit trail and approval workflow. Software controls supplement but do not replace banking reconciliation, accounting review or local statutory obligations.'],
      ['Operator responsibilities', 'Operators must manage access, incident response, backups, data retention, integrations, identity verification and lawful processing. Formal compliance certification is not claimed by this page.'],
      ['Report a concern', 'Use the Request Access page to report a suspected data or account issue. Do not transmit credentials, full identity numbers or sensitive tenant documents through the public access request form.']
    ]
  },
  'acceptable-use': {
    title: 'Acceptable use', updated: 'Draft for review · November 2026',
    intro: 'Responsible use of the platform and its operational data.',
    sections: [
      ['Respect access boundaries', 'Use only accounts and property records that you are permitted to access. Do not impersonate staff, tenants or other organizations.'],
      ['Protect operational integrity', 'Do not record false rent collections, alter evidence, evade approvals, introduce malware, attempt credential attacks or overwhelm application endpoints.'],
      ['Respect privacy', 'Upload only documents needed for legitimate rental business purposes and limit sharing to the relevant authorized users.'],
      ['Report vulnerabilities', 'Report suspected security issues through the site access request form. Avoid testing against third-party deployments without written permission.']
    ]
  },
  disclaimer: {
    title: 'Disclaimer', updated: 'Draft for review · November 2026',
    intro: 'Limitations of the information and demonstrations shown on this website.',
    sections: [
      ['Not professional advice', 'Content on this website is product information, not legal, tax, accounting, investment, property valuation or tenancy advice. Seek qualified local advice for specific decisions.'],
      ['Illustrative examples', 'Any interface preview is illustrative, not verified customer data, actual measured client performance or a service-level guarantee. Photographs are licensed architectural images and do not indicate customer relationships.'],
      ['Integrations and availability', 'Optional mobile-money, fiscal, document-storage, messaging and other features may require independent third-party approval, credentials, infrastructure and configuration.'],
      ['Accuracy', 'Product functionality and content may change. The operator should verify any promises about pricing, service levels and compliance before publication.']
    ]
  },
  accessibility: {
    title: 'Accessibility', updated: 'Draft for review · November 2026',
    intro: 'Accessibility design priorities for the KATS website and application.',
    sections: [
      ['Accessible navigation', 'The interface is designed to support keyboard-accessible menus, labeled form controls, visible focus outlines and semantic page headings.'],
      ['Motion and readability', 'The public site respects reduced-motion preferences. Text contrast, responsive layouts and legible sizing are design priorities.'],
      ['Feedback', 'Accessibility may vary by browser and device. If you encounter a barrier, explain it through the site Request Access page so it can be investigated. No formal conformance audit or certification is claimed here.']
    ]
  }
};
export const POLICY_LINKS = [
  ['Privacy', 'privacy'], ['Terms', 'terms'], ['Cookies', 'cookies'],
  ['Data protection', 'data-protection'], ['Acceptable use', 'acceptable-use'],
  ['Billing & refunds', 'refund'], ['Disclaimer', 'disclaimer'], ['Accessibility', 'accessibility']
];


/*
 * Uganda statutory context shown alongside published or draft policies.
 * This does NOT turn these summaries into a tenancy contract or replace the
 * actual operator's approved legal terms. References checked November 2026.
 */
const DPPA = ['Data Protection and Privacy Act, 2019 (Cap. 97)', 'https://ulii.org/en/akn/ug/act/2019/9/eng@2023-12-31'];
const DPPR = ['Data Protection and Privacy Regulations, 2021', 'https://ulii.org/en/akn/ug/act/si/2021/21/eng@2021-03-12'];
const LT = ['Landlord and Tenant Act, 2022 (Cap. 238)', 'https://ulii.org/en/akn/ug/act/2022/9/eng@2023-12-31'];
const LAND = ['Land Act, 1998 (Cap. 227)', 'https://ulii.org/en/akn/ug/act/1998/16/eng@2023-12-31'];
const ETA = ['Electronic Transactions Act, 2011 (Cap. 99)', 'https://ulii.org/en/akn/ug/act/2011/8/eng@2023-12-31'];
const ESA = ['Electronic Signatures Act, 2011 (Cap. 98)', 'https://ulii.org/en/akn/ug/act/2011/7/eng@2023-12-31'];
export const UGANDA_POLICY_CONTEXT = {
  privacy: {
    summary: 'Ugandan personal-data law applies to tenant, staff, owner, payment and access-request information; product features do not constitute regulatory approval.',
    sections: [
      ['Lawful processing', 'The Data Protection and Privacy Act, 2019 (Cap. 97), section 7, addresses consent and other lawful grounds, including contract performance and legal obligations. Consent given to request KATS access is not blanket consent for every subsequent use of tenancy or identity data. The responsible property operator must determine and disclose lawful purposes.'],
      ['Individual rights and records', 'Data subjects have statutory protections concerning access, correction, objection and related processing requests, subject to lawful limitations. Accounting, dispute, tenancy and tax records may require retention even where deletion is requested. Operators must assess each request under the Act and 2021 Regulations.'],
      ['Controller responsibilities', 'A deployment operator and applicable processors or collectors must assess registration with Uganda’s Personal Data Protection Office, adopt appropriate safeguards, give transparent notices and review cross-border processing under the Act. The operating organisation must identify its own privacy contact before publishing a final policy.']
    ],
    sources: [DPPA, DPPR]
  },
  terms: {
    summary: 'KATS access terms are separate from, and cannot override, a landlord–tenant agreement or mandatory Ugandan rental law.',
    sections: [
      ['Rights under tenancy law', 'The Landlord and Tenant Act, 2022 (Cap. 238) regulates qualifying residential and business premises, including rent receipts, repair obligations, deposits, fair treatment, tenancy termination and eviction procedures. Suspension of a KATS account does not terminate a tenancy or authorize the eviction of an occupant.'],
      ['Rent, records and notices', 'Sections 21–23 address rent payments, receipts, currency and accrual. Section 26 regulates rent increases, including advance notice and minimum intervals subject to the Act and agreement. A KATS reminder or status change is not necessarily service of a legally valid notice.'],
      ['Electronic agreements', 'Uganda’s Electronic Transactions Act, 2011 and Electronic Signatures Act, 2011 recognize qualifying digital records and signatures with statutory conditions and exceptions. A file upload or check-box alone does not prove that an instrument requiring special formalities is legally executed.']
    ],
    sources: [LT, ETA, ESA]
  },
  cookies: {
    summary: 'Essential security cookies are different from optional tracking; any new third-party analytics or advertising must be assessed under Ugandan privacy law.',
    sections: [
      ['Data protection and cookies', 'Where cookie values or associated identifiers are personal data, their collection and use must comply with the Data Protection and Privacy Act, 2019 and applicable 2021 Regulations, including a lawful basis and appropriate transparency. Operators must update this notice if third-party tracking or additional processors are deployed.']
    ],
    sources: [DPPA, DPPR]
  },
  refund: {
    summary: 'Platform subscription refunds, rental overpayments and tenancy security deposits are different legal matters.',
    sections: [
      ['Security deposits', 'Section 30 of the Landlord and Tenant Act, 2022 regulates security deposits for covered tenancies. It limits a landlord to one deposit not exceeding one month’s rent or one-twelfth of the annual rent, whichever is less; requires written terms for withholding and a receipt; and prohibits withholding solely for normal wear and tear.'],
      ['Rent and accounting', 'Sections 21–23 address payment receipts, agreed currency (generally Uganda shillings unless parties agree otherwise) and daily accrual of rent. An in-app reversal is not an actual bank, cash or mobile-money refund. Treat rental overpayments, prepaid rent and refundable deposits under the agreement and applicable Ugandan law.'],
      ['Disputes and possession', 'Tenancy termination, notices, rent increases, arrears and eviction are subject to the procedures and protections of the Landlord and Tenant Act, 2022, including section 26 and Parts VIII–IX. Do not apply a generic no-refunds software clause to statutory tenancy funds.']
    ],
    sources: [LT]
  },
  'data-protection': {
    summary: 'Data-protection and tenancy-security obligations apply to actual operations, not simply to software configuration.',
    sections: [
      ['Statutory safeguards', 'Section 20 of the Data Protection and Privacy Act, 2019 requires appropriate and reasonable technical and organizational controls, risk assessments and regular review. The 2021 Regulations address security, incident notification, data-subject rights and registration. Operators need actual procedures and an accountable contact.'],
      ['Tenant confidentiality', 'Identity documents, inspection photographs, rental invoices, receipts and maintenance descriptions can contain personal data. Access must be limited to lawful purposes, with role-based restrictions, controlled exports, appropriate record retention and secure disclosure. Property ownership does not automatically create unrestricted access to every person’s private data.']
    ],
    sources: [DPPA, DPPR, LT]
  },
  'acceptable-use': {
    summary: 'Responsible use includes preserving lawful tenant rights and protecting sensitive property records.',
    sections: [
      ['Lawful rental administration', 'Users must not use the platform to facilitate discriminatory letting, forged receipts, illegal lockouts, harassment, improper interference with services, or eviction outside the applicable statutory procedure. The Landlord and Tenant Act, 2022 governs the relationship of landlords and tenants for covered premises.'],
      ['Privacy and authorisation', 'Users must not expose another tenant’s personal information or process it beyond an authorised purpose. The Data Protection and Privacy Act, 2019 applies to qualifying personal-data processing and disclosures.']
    ],
    sources: [LT, DPPA]
  },
  disclaimer: {
    summary: 'KATS is a records and management system, not a registry of land title or a replacement for Uganda-qualified professional advice.',
    sections: [
      ['Legal status of property records', 'The Landlord and Tenant Act, 2022 covers qualifying tenancy arrangements, while the Land Act, 1998 (Cap. 227) addresses broader land tenure and ownership. Adding a property, lease or occupant in software does not verify title, determine lawful ownership, transfer land interests or confer a right to possession.'],
      ['Notices, taxation and evidence', 'Do not assume a digital alert, uploaded tenancy, payment record or receipt meets every legal requirement for notices, taxation, stamping, signatures or admissibility. Confirm requirements against current legislation and the facts of each transaction.']
    ],
    sources: [LT, LAND, ETA, ESA]
  },
  accessibility: {
    summary: 'Accessibility helps tenants, owners and staff understand important records without removing independent legal duties.',
    sections: [
      ['Accessible tenancy communication', 'Operators should make important notices and account information understandable and accessible, including for persons with disabilities. Applicable non-discrimination obligations under Uganda’s Landlord and Tenant Act, 2022 remain separate from technical accessibility features.']
    ],
    sources: [LT]
  }
};
