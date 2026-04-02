import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

export function LoadingBlock({ label }: { label: string }) {
  return (
    <Stack direction="row" spacing={1.5} alignItems="center" sx={{ py: 1 }}>
      <CircularProgress size={18} />
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}

export function ErrorBlock({ message }: { message: string }) {
  return (
    <Box sx={{ py: 1 }}>
      <Alert severity="error">{message}</Alert>
    </Box>
  );
}
