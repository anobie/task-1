import { Grid, List, ListItem, ListItemText, Typography } from "@mui/material";

import { getCourses, getRegistrationHistory, getRegistrationStatus } from "../../api/registration";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function StudentDashboard({ token }: { token: string }) {
  const courses = useAsyncResource(() => getCourses(token), [token]);
  const status = useAsyncResource(() => getRegistrationStatus(token), [token]);
  const history = useAsyncResource(() => getRegistrationHistory(token), [token]);

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, lg: 6 }}>
        <DashboardPanel title="Course Catalog" subtitle="Current offerings and open seats">
          {courses.isLoading && <LoadingBlock label="Loading courses" />}
          {courses.error && <ErrorBlock message={courses.error} />}
          {courses.data && (
            <List dense>
              {courses.data.slice(0, 8).map((course) => (
                <ListItem key={course.id} disablePadding>
                  <ListItemText primary={`${course.code} - ${course.title}`} secondary={`Credits: ${course.credits} | Available seats: ${course.available_seats}`} />
                </ListItem>
              ))}
              {courses.data.length === 0 && <Typography variant="body2">No courses available.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <DashboardPanel title="Enrollment Status" subtitle="Your active and historical section registrations">
          {status.isLoading && <LoadingBlock label="Loading registration status" />}
          {status.error && <ErrorBlock message={status.error} />}
          {status.data && (
            <List dense>
              {status.data.map((item) => (
                <ListItem key={item.section_id} disablePadding>
                  <ListItemText primary={`${item.course_code} (Section ${item.section_id})`} secondary={item.status} />
                </ListItem>
              ))}
              {status.data.length === 0 && <Typography variant="body2">No enrollment records yet.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <DashboardPanel title="Change History" subtitle="Recent enrollment and waitlist events">
          {history.isLoading && <LoadingBlock label="Loading enrollment history" />}
          {history.error && <ErrorBlock message={history.error} />}
          {history.data && (
            <List dense>
              {history.data.slice(0, 8).map((item) => (
                <ListItem key={item.id} disablePadding>
                  <ListItemText primary={item.event_type} secondary={`${item.details ?? "No details"} - ${new Date(item.created_at).toLocaleString()}`} />
                </ListItem>
              ))}
              {history.data.length === 0 && <Typography variant="body2">No history available.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
    </Grid>
  );
}
