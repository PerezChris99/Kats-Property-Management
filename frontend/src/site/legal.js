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
      ['Who is responsible', 'KATS is a property-management software system. The property business operating your deployment determines which tenant, lease and payment records it collects and how it uses them. For questions about your records, contact that property business or use the contact form on this site. The operator must supply its registered legal identity and privacy contact before publishing a final policy.'],
      ['Information handled', 'The system may process names, contact details, property and room references, leases, rental invoices, payment confirmations, maintenance requests, support inquiries, access logs and security events. Document uploads may contain personal information. Operators should collect only what is necessary for legitimate property operations.'],
      ['Purposes', 'Information supports property and tenancy administration, rent accounting, service requests, access control, account recovery, auditability, support and any legal obligations that apply to the operator. Payment or fiscal integrations are available only when configured and approved by the operator.'],
      ['Access and protection', 'Access is role-based and checked on the server. Sensitive workflows require authenticated accounts. Operators are responsible for safe passwords, correct role assignments, backups, secure hosting and retention decisions. No security system can guarantee zero risk.'],
      ['Sharing and processors', 'Information may be processed by hosting providers and optional payment, messaging or storage services selected by the operator. No integrations should be assumed active without configuration. Transfers and disclosures must be assessed under applicable data protection law.'],
      ['Retention and rights', 'The operator should define retention periods appropriate to its business, statutory obligations and disputes. Individuals may request access, correction, deletion or other rights where applicable through the responsible property business. Administrative privacy-request tools support tracking those requests.'],
      ['Cookies and contact', 'Essential session and CSRF cookies help secure access. See the Cookie policy for more information. Use the site contact form to send an inquiry; do not include account passwords, government identifiers or financial card information in messages.']
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
      ['Disputes', 'Send billing concerns to the property business managing your account, or submit an inquiry through the contact form for routing. Include transaction references only; never send passwords or payment card details.']
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
      ['Report a concern', 'Use the Contact page to report a suspected data or account issue. Do not transmit credentials, full identity numbers or sensitive tenant documents through the public contact form.']
    ]
  },
  'acceptable-use': {
    title: 'Acceptable use', updated: 'Draft for review · November 2026',
    intro: 'Responsible use of the platform and its operational data.',
    sections: [
      ['Respect access boundaries', 'Use only accounts and property records that you are permitted to access. Do not impersonate staff, tenants or other organizations.'],
      ['Protect operational integrity', 'Do not record false rent collections, alter evidence, evade approvals, introduce malware, attempt credential attacks or overwhelm application endpoints.'],
      ['Respect privacy', 'Upload only documents needed for legitimate rental business purposes and limit sharing to the relevant authorized users.'],
      ['Report vulnerabilities', 'Report suspected security issues through the site contact form. Avoid testing against third-party deployments without written permission.']
    ]
  },
  disclaimer: {
    title: 'Disclaimer', updated: 'Draft for review · November 2026',
    intro: 'Limitations of the information and demonstrations shown on this website.',
    sections: [
      ['Not professional advice', 'Content on this website is product information, not legal, tax, accounting, investment, property valuation or tenancy advice. Seek qualified local advice for specific decisions.'],
      ['Illustrative examples', 'All charts on the About page and example interface previews are illustrative, not measured KATS customer outcomes, actual client data or service-level guarantees. Photographs are licensed architectural imagery and do not indicate customer relationships.'],
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
      ['Feedback', 'Accessibility may vary by browser and device. If you encounter a barrier, explain it through the site Contact page so it can be investigated. No formal conformance audit or certification is claimed here.']
    ]
  }
};
export const POLICY_LINKS = [
  ['Privacy', 'privacy'], ['Terms', 'terms'], ['Cookies', 'cookies'],
  ['Data protection', 'data-protection'], ['Acceptable use', 'acceptable-use'],
  ['Billing & refunds', 'refund'], ['Disclaimer', 'disclaimer'], ['Accessibility', 'accessibility']
];
