"use client";

import { useNativeBackButton } from "@/app/hooks/use-native-back-button";

export function NativeBackHandler() {
  useNativeBackButton();
  return null;
}
