import { writable } from 'svelte/store';

export interface DisplayState {
	recipient: { id: number; first_name: string; reassurance_message: string; photo_path: string | null } | null;
	household: { id: number; display_name: string; reassurance_message: string; photo_path: string | null } | null;
	people: Array<{ id: number; first_name: string; relation: string; photo_path: string | null; message: string | null; next_visit: string | null; is_primary_caregiver: boolean }>;
	events_today: Array<{ id: number; title: string; event_time: string | null; message_before: string | null; message_during: string | null; message_after: string | null }>;
	faqs: Array<{ id: number; question: string; answer: string }>;
	daily_message: { content: string; author: string | null } | null;
	server_time: string;
}

export const displayState = writable<DisplayState | null>(null);

export const API = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
