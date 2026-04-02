import { useMemo, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Typography
} from "@mui/material";

import {
  dropSection,
  enrollInSection,
  getCourseDetail,
  getCourses,
  getEligibility,
  getRegistrationHistory,
  getRegistrationStatus,
  joinWaitlist
} from "../../api/registration";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

function errorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (typeof detail === "object" && detail !== null && "reasons" in (detail as object)) {
      const reasons = (detail as { reasons?: string[] }).reasons;
      if (Array.isArray(reasons) && reasons.length > 0) {
        return reasons.join(" ");
      }
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Operation failed.";
}

export function StudentDashboard({ token }: { token: string }) {
  const courses = useAsyncResource(() => getCourses(token), [token]);
  const status = useAsyncResource(() => getRegistrationStatus(token), [token]);
  const history = useAsyncResource(() => getRegistrationHistory(token), [token]);

  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionResult, setActionResult] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const details = useAsyncResource(
    () => (selectedCourseId ? getCourseDetail(token, selectedCourseId) : Promise.resolve(null)),
    [token, selectedCourseId]
  );

  const eligibility = useAsyncResource(
    () => (selectedCourseId && selectedSectionId ? getEligibility(token, selectedCourseId, selectedSectionId) : Promise.resolve(null)),
    [token, selectedCourseId, selectedSectionId]
  );

  const currentSectionId = useMemo(() => {
    const active = status.data?.find((item) => item.status === "ENROLLED");
    return active?.section_id ?? null;
  }, [status.data]);

  const runRegistrationAction = async (action: "enroll" | "waitlist" | "drop") => {
    const sectionId = action === "drop" ? currentSectionId : selectedSectionId;
    if (!sectionId) {
      setActionError("Select a section first.");
      return;
    }
    setActionError(null);
    setActionResult(null);
    setIsSubmitting(true);
    try {
      if (action === "enroll") {
        const response = await enrollInSection(token, sectionId);
        setActionResult(`Enrollment result: ${response.status}`);
      } else if (action === "waitlist") {
        const response = await joinWaitlist(token, sectionId);
        setActionResult(`Waitlist result: ${response.status}`);
      } else {
        const response = await dropSection(token, sectionId);
        setActionResult(`Drop result: ${response.status}`);
      }
      await Promise.all([status.reload(), history.reload(), courses.reload()]);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

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
        <DashboardPanel title="Registration Actions" subtitle="Enroll, waitlist, and drop from your current workspace">
          <Stack spacing={1.5}>
            <TextField
              select
              size="small"
              label="Course"
              value={selectedCourseId ?? ""}
              onChange={(event) => {
                const nextCourse = Number(event.target.value);
                setSelectedCourseId(nextCourse);
                setSelectedSectionId(null);
                setActionError(null);
                setActionResult(null);
              }}
            >
              {(courses.data ?? []).map((course) => (
                <MenuItem key={course.id} value={course.id}>
                  {course.code} - {course.title}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              size="small"
              label="Section"
              value={selectedSectionId ?? ""}
              disabled={!selectedCourseId || !details.data}
              onChange={(event) => {
                setSelectedSectionId(Number(event.target.value));
                setActionError(null);
                setActionResult(null);
              }}
            >
              {(details.data?.sections ?? []).map((section) => (
                <MenuItem key={section.id} value={section.id}>
                  {section.code} (id {section.id}) cap {section.capacity}
                </MenuItem>
              ))}
            </TextField>

            {eligibility.data && (
              <Box>
                {eligibility.data.eligible ? <Chip size="small" color="success" label="Eligible" /> : <Chip size="small" color="warning" label="Not Eligible" />}
                {!eligibility.data.eligible && eligibility.data.reasons.length > 0 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                    {eligibility.data.reasons.join(" ")}
                  </Typography>
                )}
              </Box>
            )}

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button variant="contained" disabled={isSubmitting || !selectedSectionId} onClick={() => void runRegistrationAction("enroll")}>
                Enroll
              </Button>
              <Button variant="outlined" disabled={isSubmitting || !selectedSectionId} onClick={() => void runRegistrationAction("waitlist")}>
                Join Waitlist
              </Button>
              <Button variant="outlined" color="warning" disabled={isSubmitting || !currentSectionId} onClick={() => void runRegistrationAction("drop")}>
                Drop Current
              </Button>
            </Stack>

            {actionResult && <Alert severity="success">{actionResult}</Alert>}
            {actionError && <Alert severity="error">{actionError}</Alert>}
          </Stack>
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
