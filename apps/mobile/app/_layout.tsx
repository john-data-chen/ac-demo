import "../global.css";
import "@/lib/i18n";

import { DarkTheme, ThemeProvider } from "@react-navigation/native";
import { QueryClientProvider } from "@tanstack/react-query";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { useColorScheme, View as RNView, Text as RNText } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import Toast from "react-native-toast-message";

import { useAuth } from "@/hooks/use-auth";
import { queryClient } from "@/lib/query-client";
import { applyThemePreference, loadThemePreference } from "@/lib/theme";
import { View, ActivityIndicator } from "@/lib/tw";

export { ErrorBoundary } from "expo-router";

// Toast uses the OPPOSITE theme of the UI: light UI → dark toast, dark UI → light toast.
// Palettes mirror global.css --color-card/-foreground/-border/-primary.
const TOAST_PALETTE = {
  light: {
    card: "hsl(180 35% 98%)",
    fg: "hsl(180 45% 10%)",
    border: "hsl(180 20% 92%)",
    primary: "hsl(180 75% 35%)"
  },
  dark: {
    card: "hsl(180 35% 8%)",
    fg: "hsl(180 20% 98%)",
    border: "hsl(180 20% 18%)",
    primary: "hsl(180 75% 45%)"
  }
};

function SyncToast({ text1 }: { text1?: string }) {
  const c = useColorScheme() === "dark" ? TOAST_PALETTE.light : TOAST_PALETTE.dark;
  return (
    <RNView
      style={{
        marginHorizontal: 16,
        flexDirection: "row",
        alignItems: "center",
        gap: 8,
        borderRadius: 6,
        borderWidth: 1,
        borderColor: c.border,
        backgroundColor: c.card,
        paddingHorizontal: 16,
        paddingVertical: 12,
        shadowColor: "#000",
        shadowOpacity: 0.15,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: 4
      }}
    >
      <RNText style={{ fontWeight: "700", color: c.primary }}>✓</RNText>
      <RNText style={{ fontWeight: "500", color: c.fg }}>{text1}</RNText>
    </RNView>
  );
}

const toastConfig = {
  sync: (props: { text1?: string }) => <SyncToast {...props} />
};

function RootLayoutNav() {
  const segments = useSegments();
  const router = useRouter();
  const { session, isLoading } = useAuth();
  const [isNavigationReady, setIsNavigationReady] = useState(false);

  useEffect(() => {
    setIsNavigationReady(true);
  }, []);

  // Restore persisted theme preference on mount
  useEffect(() => {
    loadThemePreference().then((pref) => {
      applyThemePreference(pref);
    });
  }, []);

  useEffect(() => {
    if (isLoading || !isNavigationReady) {
      return;
    }

    const inAuthGroup = segments[0] === "(auth)";

    if (!session && !inAuthGroup) {
      router.replace("/(auth)/login");
    } else if (session && inAuthGroup) {
      router.replace("/(tabs)");
    }
  }, [session, segments, isLoading, isNavigationReady, router]);

  if (isLoading || !isNavigationReady) {
    return (
      <View className="flex-1 items-center justify-center bg-background">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ThemeProvider value={DarkTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="boards" options={{ headerShown: false }} />
        <Stack.Screen name="tasks" options={{ headerShown: false }} />
        <Stack.Screen name="projects" options={{ headerShown: false }} />
      </Stack>
      <StatusBar style="light" />
      <Toast config={toastConfig} />
    </ThemeProvider>
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <RootLayoutNav />
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
