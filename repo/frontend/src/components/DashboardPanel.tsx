import { Card, CardContent, Stack, Typography } from "@mui/material";

export function DashboardPanel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent>
        <Stack spacing={1.25}>
          <Typography variant="h6">{title}</Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
          {children}
        </Stack>
      </CardContent>
    </Card>
  );
}
