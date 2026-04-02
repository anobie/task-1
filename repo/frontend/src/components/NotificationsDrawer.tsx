import CloseIcon from "@mui/icons-material/Close";
import { Box, Divider, Drawer, IconButton, List, ListItem, ListItemText, Stack, Typography } from "@mui/material";

type NotificationItem = {
  id: number;
  title: string;
  message: string;
  read: boolean;
  delivered_at: string;
};

type NotificationsDrawerProps = {
  open: boolean;
  items: NotificationItem[];
  onClose: () => void;
  onMarkRead: (id: number) => void;
};

export function NotificationsDrawer({ open, items, onClose, onMarkRead }: NotificationsDrawerProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: 360, p: 2 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="h6">Notifications</Typography>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Stack>
        <Divider />
        <List>
          {items.map((item) => (
            <ListItem key={item.id} alignItems="flex-start" disablePadding sx={{ py: 1.25 }}>
              <ListItemText
                primary={item.title}
                secondary={`${item.message} - ${new Date(item.delivered_at).toLocaleString()}`}
                primaryTypographyProps={{ fontWeight: item.read ? 500 : 700 }}
                onClick={() => {
                  if (!item.read) {
                    onMarkRead(item.id);
                  }
                }}
                sx={{ cursor: "pointer" }}
              />
            </ListItem>
          ))}
          {items.length === 0 && (
            <ListItem>
              <ListItemText primary="No notifications yet" secondary="Triggered messages will appear here." />
            </ListItem>
          )}
        </List>
      </Box>
    </Drawer>
  );
}
