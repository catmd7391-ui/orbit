// src/supabaseClient.js
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = "https://wradgttjaslnajwjlsio.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_p3n3xlJrqn-y3Fu3NysmUg_6JzfeMFMs";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);