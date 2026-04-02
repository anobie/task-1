import { Grid, List, ListItem, ListItemText, Typography } from "@mui/material";

import { getArrears } from "../../api/finance";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function FinanceDashboard({ token }: { token: string }) {
  const arrears = useAsyncResource(() => getArrears(token), [token]);

  return (
    <Grid container spacing={2.5}>
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
