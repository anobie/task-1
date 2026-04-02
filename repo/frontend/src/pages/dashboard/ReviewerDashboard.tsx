import { Grid, List, ListItem, ListItemText, Typography } from "@mui/material";

import { getOutliers, getReviewAssignments } from "../../api/reviews";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

const DEFAULT_ROUND_ID = 1;

export function ReviewerDashboard({ token, roleLabel }: { token: string; roleLabel: string }) {
  const assignments = useAsyncResource(() => getReviewAssignments(token, DEFAULT_ROUND_ID), [token]);
  const outliers = useAsyncResource(() => getOutliers(token, DEFAULT_ROUND_ID), [token]);

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, md: 7 }}>
        <DashboardPanel title={`${roleLabel} Workbench`} subtitle="Assigned submissions and visibility policy by round">
          {assignments.isLoading && <LoadingBlock label="Loading assignments" />}
          {assignments.error && <ErrorBlock message={assignments.error} />}
          {assignments.data && (
            <List dense>
              {assignments.data.map((item) => (
                <ListItem key={item.id} disablePadding>
                  <ListItemText
                    primary={`Assignment #${item.id} - Section ${item.section_id}`}
                    secondary={item.student_id === null ? "Blind mode identity hidden" : `Student ID: ${item.student_id}`}
                  />
                </ListItem>
              ))}
              {assignments.data.length === 0 && <Typography variant="body2">No assignments available.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
      <Grid size={{ xs: 12, md: 5 }}>
        <DashboardPanel title="Outlier Flags" subtitle="Deviation monitoring across submitted scores">
          {outliers.isLoading && <LoadingBlock label="Loading outlier flags" />}
          {outliers.error && <ErrorBlock message={outliers.error} />}
          {outliers.data && (
            <List dense>
              {outliers.data.map((flag) => (
                <ListItem key={flag.id} disablePadding>
                  <ListItemText primary={`Flag #${flag.id} - Deviation ${flag.deviation.toFixed(2)}`} secondary={flag.resolved ? "Resolved" : "Unresolved"} />
                </ListItem>
              ))}
              {outliers.data.length === 0 && <Typography variant="body2">No outlier flags.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
    </Grid>
  );
}
