# Metered utilities and controlled billing

Kats tracks water (m³) and electricity (kWh) using integer thousandths of a
unit. A reported reading is *not a bill*. A separate accountant/owner may add
a positive reading charge to the existing, unpaid invoice covering its date.
This is not an automated payment or regulatory tax invoice.

## Sequence

1. Owner or manager registers a room's utility meter, baseline and approved
   rate in integer UGX per whole unit.
2. Assigned caretaker or authorized staff records a meter reading and the date;
   sequential readings must not decrease. Idempotency keys protect retries.
3. The app calculates incremental charge with integer arithmetic and snapshots
   the tariff. Any later tariff change must be separately designed as an
   effective-dated rate; editing the historic reading is forbidden.
4. **Independent** owner/accountant checks meter evidence, contract and invoice,
   then attaches the charge once to the unpaid covering invoice.
5. Tenant reads scoped usage and the invoice. The invoice remains a normal
   non-fiscal accounting document pending URA EFRIS acceptance.

Shared/common-area allocation, disputed readings, prepaid UMEME tokens,
differing landlord tariff obligations and tariff histories need separately
approved policies and are not represented by this simple meter model.
