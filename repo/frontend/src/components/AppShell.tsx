import MenuIcon from "@mui/icons-material/Menu";
import NotificationsIcon from "@mui/icons-material/Notifications";
import LogoutIcon from "@mui/icons-material/Logout";
import {
  AppBar,
  Badge,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Toolbar,
  Typography
} from "@mui/material";
import { useState } from "react";

export type NavItem = {
  label: string;
  active?: boolean;
  onClick: () => void;
};

type AppShellProps = {
  title: string;
  subtitle: string;
  navItems: NavItem[];
  unreadCount: number;
  onNotificationsClick: () => void;
  onLogout: () => void;
  children: React.ReactNode;
};

const drawerWidth = 250;

export function AppShell({
  title,
  subtitle,
  navItems,
  unreadCount,
  onNotificationsClick,
  onLogout,
  children
}: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const drawer = (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" color="primary.dark" sx={{ mb: 2 }}>
        CEMS Portal
      </Typography>
      <List>
        {navItems.map((item) => (
          <ListItemButton
            key={item.label}
            selected={Boolean(item.active)}
            onClick={() => {
              item.onClick();
              setMobileOpen(false);
            }}
            sx={{ borderRadius: 2, mb: 0.5 }}
          >
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar position="fixed" sx={{ ml: { md: `${drawerWidth}px` }, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar>
          <IconButton aria-label="open navigation" color="inherit" edge="start" onClick={() => setMobileOpen((prev) => !prev)} sx={{ mr: 2, display: { md: "none" } }}>
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{title}</Typography>
            <Typography variant="caption" sx={{ opacity: 0.86 }}>
              {subtitle}
            </Typography>
          </Box>
          <Stack direction="row" spacing={0.5}>
            <IconButton aria-label="open notifications" color="inherit" onClick={onNotificationsClick}>
              <Badge badgeContent={unreadCount} color="secondary">
                <NotificationsIcon />
              </Badge>
            </IconButton>
            <IconButton aria-label="logout" color="inherit" onClick={onLogout}>
              <LogoutIcon />
            </IconButton>
          </Stack>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: drawerWidth } }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{ display: { xs: "none", md: "block" }, "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" } }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 3 }, mt: 9 }}>
        {children}
      </Box>
    </Box>
  );
}
