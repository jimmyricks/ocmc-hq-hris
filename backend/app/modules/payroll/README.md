# Payroll rate and snapshot policy

- An employee override is unique for `(workspace, task type, employee)`. It takes
  precedence over the task type's workspace default; both rates must be positive.
- A task submission is eligible for payroll only after approval. Approval stores
  the selected rate, quantity, and amount on the submission and credits the
  employee ledger for that same decimal amount. Later rate edits do not change
  an approved submission.
- Payroll period membership uses `submitted_at`, inclusively from `start_date`
  through `cutoff` (`end_date` when no cutoff is set). Approval time does not
  determine the period.
- Quantity is explicitly `1.00` per approved deliverable. `per_hour` task types
  are rejected until the product captures hours; a rate is never silently
  interpreted as hours worked.
- Existing approved submissions have no trustworthy historical snapshot.
  Migration leaves their snapshot fields null and warns for manual review.
  Generation rejects them until the historical amount is explicitly resolved;
  it does not infer pay from today's rate.
- Payroll generation may be repeated only while all generated entries are draft
  or under review. It replaces those entries from approved snapshots. Approved
  or paid entries are protected. Payment reconciles entry and line totals and
  creates at most one invoice and payroll debit per entry.
