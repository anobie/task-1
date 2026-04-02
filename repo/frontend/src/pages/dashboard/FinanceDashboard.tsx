import { useState } from "react";

import { Alert, Button, Grid, List, ListItem, ListItemText, MenuItem, Stack, TextField, Typography } from "@mui/material";

import {
  getArrears,
  importReconciliationCsv,
  postDeposit,
  postMonthEndBilling,
  postPayment,
  postPrepayment,
  postRefund
} from "../../api/finance";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function FinanceDashboard({ token }: { token: string }) {
  const arrears = useAsyncResource(() => getArrears(token), [token]);

  const [entryType, setEntryType] = useState("PAYMENT");
  const [studentId, setStudentId] = useState("");
  const [amount, setAmount] = useState("");
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [instrument, setInstrument] = useState("CASH");
  const [description, setDescription] = useState("Posted via finance desk");
  const [referenceEntryId, setReferenceEntryId] = useState("");
  const [csvText, setCsvText] = useState("student_id,amount,statement_date\n");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmitEntry = async () => {
    setIsSubmitting(true);
    setResult(null);
    setError(null);
    try {
      const payload = {
        student_id: Number(studentId),
        amount: Number(amount),
        entry_date: entryDate,
        instrument,
        description,
        reference_entry_id: referenceEntryId ? Number(referenceEntryId) : undefined
      };
      if (entryType === "PAYMENT") {
        await postPayment(token, payload);
      } else if (entryType === "PREPAYMENT") {
        await postPrepayment(token, payload);
      } else if (entryType === "DEPOSIT") {
        await postDeposit(token, payload);
      } else if (entryType === "REFUND") {
        await postRefund(token, payload);
      } else {
        await postMonthEndBilling(token, payload);
      }
      setResult(`${entryType} posted successfully.`);
      await arrears.reload();
    } catch (submitError) {
      if (submitError instanceof Error) {
        setError(submitError.message);
      } else {
        setError("Finance operation failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const onImportCsv = async () => {
    setIsSubmitting(true);
    setResult(null);
    setError(null);
    try {
      const report = await importReconciliationCsv(token, csvText);
      setResult(`Imported reconciliation ${report.import_id} (matched ${report.matched_total.toFixed(2)}).`);
    } catch (submitError) {
      if (submitError instanceof Error) {
        setError(submitError.message);
      } else {
        setError("CSV import failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, md: 6 }}>
        <DashboardPanel title="Posting Desk" subtitle="Post payments, deposits, refunds, and month-end billing">
          <Stack spacing={1.1}>
            <TextField select size="small" label="Entry Type" value={entryType} onChange={(event) => setEntryType(event.target.value)}>
              <MenuItem value="PAYMENT">Payment</MenuItem>
              <MenuItem value="PREPAYMENT">Prepayment</MenuItem>
              <MenuItem value="DEPOSIT">Deposit</MenuItem>
              <MenuItem value="REFUND">Refund</MenuItem>
              <MenuItem value="MONTH_END_BILLING">Month-End Billing</MenuItem>
            </TextField>
            <TextField size="small" type="number" label="Student ID" value={studentId} onChange={(event) => setStudentId(event.target.value)} />
            <TextField size="small" type="number" label="Amount" value={amount} onChange={(event) => setAmount(event.target.value)} />
            <TextField size="small" type="date" label="Entry Date" value={entryDate} onChange={(event) => setEntryDate(event.target.value)} InputLabelProps={{ shrink: true }} />
            {entryType !== "MONTH_END_BILLING" && (
              <TextField select size="small" label="Instrument" value={instrument} onChange={(event) => setInstrument(event.target.value)}>
                <MenuItem value="CASH">Cash</MenuItem>
                <MenuItem value="CHECK">Check</MenuItem>
                <MenuItem value="INTERNAL_TRANSFER">Internal Transfer</MenuItem>
              </TextField>
            )}
            {entryType === "REFUND" && (
              <TextField
                size="small"
                type="number"
                label="Reference Entry ID"
                value={referenceEntryId}
                onChange={(event) => setReferenceEntryId(event.target.value)}
              />
            )}
            <TextField size="small" label="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
            <Button variant="contained" disabled={isSubmitting} onClick={() => void onSubmitEntry()}>
              Post Entry
            </Button>
            {result && <Alert severity="success">{result}</Alert>}
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DashboardPanel>
      </Grid>

      <Grid size={{ xs: 12, md: 6 }}>
        <DashboardPanel title="Reconciliation Import" subtitle="Upload statement CSV and generate match totals">
          <Stack spacing={1.1}>
            <TextField
              multiline
              minRows={8}
              label="CSV Content"
              value={csvText}
              onChange={(event) => setCsvText(event.target.value)}
              placeholder="student_id,amount,statement_date"
            />
            <Button variant="outlined" disabled={isSubmitting} onClick={() => void onImportCsv()}>
              Import CSV
            </Button>
          </Stack>
        </DashboardPanel>
      </Grid>

      <Grid size={{ xs: 12 }}>
        <DashboardPanel title="Arrears & Late Fees" subtitle="Overdue balances after grace period and monthly fee policy">
          {arrears.isLoading && <LoadingBlock label="Loading arrears" />}
          {arrears.error && <ErrorBlock message={arrears.error} />}
          {arrears.data && (
            <List dense>
              {arrears.data.map((item) => (
                <ListItem key={item.student_id} disablePadding>
                  <ListItemText primary={`Student ${item.student_id}`} secondary={`Balance: $${item.balance.toFixed(2)} | Overdue: ${item.overdue_days} days`} />
                </ListItem>
              ))}
              {arrears.data.length === 0 && <Typography variant="body2">No overdue balances currently.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
    </Grid>
  );
}
