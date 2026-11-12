import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env["VITE_SUPABASE_URL"]?.trim();
const supabasePublishableKey = import.meta.env[
  "VITE_SUPABASE_PUBLISHABLE_KEY"
]?.trim();

export const isSupabaseConfigured = Boolean(
  supabaseUrl && supabasePublishableKey,
);
export const isSupabaseConfigurationIncomplete =
  Boolean(supabaseUrl) !== Boolean(supabasePublishableKey);

export const supabase =
  supabaseUrl && supabasePublishableKey
    ? createClient(supabaseUrl, supabasePublishableKey, {
        auth: {
          autoRefreshToken: true,
          detectSessionInUrl: false,
          persistSession: false,
        },
      })
    : null;
