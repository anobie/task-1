import { useMemo, useState } from "react";

import { Alert, Button, Grid, List, ListItem, ListItemText, MenuItem, Stack, TextField, Typography } from "@mui/material";

import {
  assignRecheck,
  autoAssign,
  createRecheck,
  getOutliers,
  getReviewAssignments,
  manualAssign,
  submitScore
} from "../../api/reviews";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

const DEFAULT_ROUND_ID = 1;

export function ReviewerDashboard({ token, roleLabel }: { token: string; roleLabel: string }) {
  const [roundId, setRoundId] = useState(DEFAULT_ROUND_ID);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number | null>(null);
  const [criterionJson, setCriterionJson] = useState('{"Quality": 4, "Completeness": 4}');
  const [comment, setComment] = useState("Submitted from reviewer workbench");

  const [manualReviewerId, setManualReviewerId] = useState("");
  const [manualStudentId, setManualStudentId] = useState("");
  const [autoStudentIds, setAutoStudentIds] = useState("");
  const [autoPerStudent, setAutoPerStudent] = useState("1");
  const [recheckId, setRecheckId] = useState("");
  const [recheckReviewerId, setRecheckReviewerId] = useState("");

  const [studentRecheckStudentId, setStudentRecheckStudentId] = useState("");
  const [studentRecheckSectionId, setStudentRecheckSectionId] = useState("");
  const [studentRecheckReason, setStudentRecheckReason] = useState("Please review scoring fairness.");

  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const assignments = useAsyncResource(() => getReviewAssignments(token, roundId), [token, roundId]);
  const outliers = useAsyncResource(
    () => (roleLabel === "Instructor" ? getOutliers(token, roundId) : Promise.resolve([])),
    [token, roundId, roleLabel]
  );

  const isInstructor = roleLabel === "Instructor";

  const assignmentOptions = useMemo(() => assignments.data ?? [], [assignments.data]);

  const runAction = async (callback: () => Promise<void>) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await callback();
      await assignments.reload();
      if (isInstructor) {
        await outliers.reload();
      }
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Action failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSubmitScore = async () => {
    if (!selectedAssignmentId) {
      setErrorMessage("Pick an assignment first.");
      return;
    }
    let parsed: Record<string, number>;
    try {
      parsed = JSON.parse(criterionJson) as Record<string, number>;
    } catch {
      setErrorMessage("Criterion scores must be valid JSON.");
      return;
    }
    await runAction(async () => {
      const response = await submitScore(token, { assignment_id: selectedAssignmentId, criterion_scores: parsed, comment });
      setSuccessMessage(`Score submitted. Total: ${response.total_score}`);
    });
  };

  const onManualAssign = async () => {
    await runAction(async () => {
      await manualAssign(token, roundId, Number(manualReviewerId), Number(manualStudentId));
      setSuccessMessage("Manual assignment created.");
    });
  };

  const onAutoAssign = async () => {
    const studentIds = autoStudentIds
      .split(",")
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value) && value > 0);
    await runAction(async () => {
      const response = await autoAssign(token, roundId, studentIds, Number(autoPerStudent));
      setSuccessMessage(`Auto assignment created: ${response.created_assignments}`);
    });
  };

  const onAssignRecheck = async () => {
    await runAction(async () => {
      await assignRecheck(token, Number(recheckId), Number(recheckReviewerId));
      setSuccessMessage("Recheck assigned.");
    });
  };

  const onCreateRecheck = async () => {
    await runAction(async () => {
      const response = await createRecheck(token, {
        round_id: roundId,
        student_id: Number(studentRecheckStudentId),
        section_id: Number(studentRecheckSectionId),
        reason: studentRecheckReason
      });
      setSuccessMessage(`Recheck created: #${response.id}`);
    });
  };

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12 }}>
        <DashboardPanel title="Round Selector" subtitle="Choose round context for assignment and scoring actions">
          <TextField
            type="number"
            size="small"
            label="Round ID"
            value={roundId}
            onChange={(event) => setRoundId(Number(event.target.value || DEFAULT_ROUND_ID))}
            sx={{ maxWidth: 220 }}
          />
          {successMessage && <Alert severity="success">{successMessage}</Alert>}
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
        </DashboardPanel>
      </Grid>
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

          {!isInstructor && (
            <Stack spacing={1.25} sx={{ mt: 1 }}>
              <TextField
                select
                size="small"
                label="Assignment"
                value={selectedAssignmentId ?? ""}
                onChange={(event) => setSelectedAssignmentId(Number(event.target.value))}
              >
                {assignmentOptions.map((assignment) => (
                  <MenuItem key={assignment.id} value={assignment.id}>
                    Assignment #{assignment.id} (section {assignment.section_id})
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                label="Criterion Scores JSON"
                value={criterionJson}
                onChange={(event) => setCriterionJson(event.target.value)}
              />
              <TextField size="small" label="Comment" value={comment} onChange={(event) => setComment(event.target.value)} />
              <Button variant="contained" disabled={isSubmitting} onClick={() => void onSubmitScore()}>
                Submit Score
              </Button>
            </Stack>
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
              {outliers.data.length === 0 && <Typography variant="body2">No outlier flags or unavailable for this role.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>

      {isInstructor && (
        <>
          <Grid size={{ xs: 12, md: 6 }}>
            <DashboardPanel title="Assignment Controls" subtitle="Manual and automatic assignment operations">
              <Stack spacing={1}>
                <TextField size="small" label="Manual Reviewer ID" value={manualReviewerId} onChange={(event) => setManualReviewerId(event.target.value)} />
                <TextField size="small" label="Manual Student ID" value={manualStudentId} onChange={(event) => setManualStudentId(event.target.value)} />
                <Button variant="contained" disabled={isSubmitting} onClick={() => void onManualAssign()}>
                  Create Manual Assignment
                </Button>

                <TextField
                  size="small"
                  label="Auto Student IDs (comma-separated)"
                  value={autoStudentIds}
                  onChange={(event) => setAutoStudentIds(event.target.value)}
                />
                <TextField size="small" type="number" label="Reviewers per Student" value={autoPerStudent} onChange={(event) => setAutoPerStudent(event.target.value)} />
                <Button variant="outlined" disabled={isSubmitting} onClick={() => void onAutoAssign()}>
                  Run Auto Assignment
                </Button>
              </Stack>
            </DashboardPanel>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <DashboardPanel title="Recheck Controls" subtitle="Create and assign recheck requests">
              <Stack spacing={1}>
                <TextField
                  size="small"
                  label="Student ID for Recheck"
                  value={studentRecheckStudentId}
                  onChange={(event) => setStudentRecheckStudentId(event.target.value)}
                />
                <TextField
                  size="small"
                  label="Section ID for Recheck"
                  value={studentRecheckSectionId}
                  onChange={(event) => setStudentRecheckSectionId(event.target.value)}
                />
                <TextField
                  size="small"
                  label="Reason"
                  value={studentRecheckReason}
                  onChange={(event) => setStudentRecheckReason(event.target.value)}
                />
                <Button variant="outlined" disabled={isSubmitting} onClick={() => void onCreateRecheck()}>
                  Create Recheck
                </Button>

                <TextField size="small" label="Recheck ID" value={recheckId} onChange={(event) => setRecheckId(event.target.value)} />
                <TextField size="small" label="Assign Reviewer ID" value={recheckReviewerId} onChange={(event) => setRecheckReviewerId(event.target.value)} />
                <Button variant="contained" disabled={isSubmitting} onClick={() => void onAssignRecheck()}>
                  Assign Recheck
                </Button>
              </Stack>
            </DashboardPanel>
          </Grid>
        </>
      )}

      {!isInstructor && (
        <Grid size={{ xs: 12 }}>
          <DashboardPanel title="Recheck Request" subtitle="Student self-service request creation for current round">
            <Stack spacing={1}>
              <TextField size="small" label="Your Student ID" value={studentRecheckStudentId} onChange={(event) => setStudentRecheckStudentId(event.target.value)} />
              <TextField size="small" label="Section ID" value={studentRecheckSectionId} onChange={(event) => setStudentRecheckSectionId(event.target.value)} />
              <TextField size="small" label="Reason" value={studentRecheckReason} onChange={(event) => setStudentRecheckReason(event.target.value)} />
              <Button variant="outlined" disabled={isSubmitting} onClick={() => void onCreateRecheck()}>
                Submit Recheck Request
              </Button>
            </Stack>
          </DashboardPanel>
        </Grid>
      )}
    </Grid>
  );
}
