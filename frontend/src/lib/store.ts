import { writable } from 'svelte/store';

export interface DisplayState {
	recipient: { id: number; first_name: string; reassurance_message: string; photo_path: string | null } | null;
	household: { id: number; display_name: string; reassurance_message: string; photo_path: string | null } | null;
	people: Array<{ id: number; first_name: string; relation: string; photo_path: string | null; message: string | null; next_visit: string | null; is_primary_caregiver: boolean }>;
	events_today: Array<{ id: number; title: string; event_time: string | null; message_before: string | null; message_during: string | null; message_after: string | null }>;
	faqs: Array<{ id: number; question: string; answer: string }>;
	daily_message: { content: string; author: string | null } | null;
	night_start: string;
	night_end: string;
	ha_states: Array<{ entity_id: string; label: string; icon: string; unit: string; state: string; state_on_label?: string | null; state_off_label?: string | null; state_on_color?: string | null; state_off_color?: string | null }>;
	photos: Array<{ id: number; path: string; caption: string | null; display_order: number }>;
	weather: Array<{ date: string; day: string; icon: string; label: string; tmax: number; tmin: number }>;
	birthdays: Array<{ first_name: string; relation: string; photo_path: string | null; days_until: number; age: number }>;
	ha_position: string;
	present_person_ids: number[];
	server_time: string;
}

export const displayState = writable<DisplayState | null>(null);

function resolveApiUrl(): string {
	// Variable d'env explicite → prioritaire (utile si le backend est sur un autre hôte)
	if (import.meta.env.PUBLIC_API_URL) return import.meta.env.PUBLIC_API_URL;
	// En production, le serveur frontend proxie /api, /media et /ws vers le backend.
	// On utilise donc des URLs relatives (même origine) — fonctionne en local (IP:3000)
	// comme à distance (https://votre-domaine.tld/) via le reverse proxy.
	if (import.meta.env.PROD) return '';
	// En dev (vite), le backend est sur localhost:8000
	if (typeof window !== 'undefined') {
		return `${window.location.protocol}//${window.location.hostname}:8000`;
	}
	return 'http://localhost:8000';
}

export const API = resolveApiUrl();