# Payroll rate and snapshot policy

- An employee override is unique for `(workspace, task type, employee)`. It takes
  precedence over the task type's workspace default; both rates must be positive.
- Payroll periods are the 1st–14th and the 15th through the calendar month's
  final day. The date ranges are inclusive, and a period's cutoff must equal its
  end date.
- A task is eligible only when it has an approved submission and is currently
  `done`. Period membership uses the recorded transition into `done`, not its
  submission or approval timestamp. Payroll generation does not change task
  status.
- Approval stores the selected rate, quantity, and amount on the submission
  and credits the employee ledger for that same decimal amount. Later rate edits
  do not change an approved submission.
- Quantity is explicitly `1.00` per approved deliverable. `per_hour` task types
  are rejected until the product captures hours; a rate is never silently
  interpreted as hours worked.
- Existing approved submissions may have no trustworthy historical snapshot,
  and legacy `done` tasks may have no recorded Done transition date. Generation
  rejects either case for manual review; it does not infer a date or amount.
- Payroll generation may be repeated only while all generated entries are draft
  or under review. It replaces those entries from approved snapshots and
  prevents a submission from appearing in multiple periods. Approved or paid
  entries are protected.
- HR approval issues an employee-readable invoice. Payment reconciles entry,
  line-item, and invoice totals, marks the invoice paid, and creates at most one
  payroll debit per entry.
