export function isNightTime(now: Date, nightStart: string, nightEnd: string): boolean {
	const toMin = (hhmm: string) => {
		const [h, m] = hhmm.split(':').map(Number);
		return h * 60 + m;
	};
	const cur = now.getHours() * 60 + now.getMinutes();
	const start = toMin(nightStart);
	const end = toMin(nightEnd);
	// Gère le cas qui passe minuit (ex: 21:30 → 07:00)
	return start > end ? cur >= start || cur < end : cur >= start && cur < end;
}

export function getMoment(hour: number, nightStart = '21:30', nightEnd = '07:00'): 'nuit' | 'matin' | 'apres-midi' | 'soir' {
	const d = new Date();
	d.setHours(hour, 0, 0, 0);
	if (isNightTime(d, nightStart, nightEnd)) return 'nuit';
	if (hour >= 6 && hour < 12) return 'matin';
	if (hour >= 12 && hour < 18) return 'apres-midi';
	return 'soir';
}

export function getMomentLabel(moment: string): string {
	switch (moment) {
		case 'nuit': return 'NUIT';
		case 'matin': return 'MATIN';
		case 'apres-midi': return 'APRÈS-MIDI';
		case 'soir': return 'SOIR';
		default: return '';
	}
}

const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];

export function formatDate(d: Date): string {
	const jour = JOURS[d.getDay()];
	const mois = MOIS[d.getMonth()];
	return `${jour} ${d.getDate()} ${mois} ${d.getFullYear()}`;
}

export function formatTime(d: Date): string {
	const h = d.getHours().toString().padStart(2, '0');
	const m = d.getMinutes().toString().padStart(2, '0');
	return `${h} h ${m}`;
}

export function eventStatus(eventTime: string | null, now: Date): 'before' | 'during' | 'after' {
	if (!eventTime) return 'before';
	const [h, min] = eventTime.split(':').map(Number);
	const eventMinutes = h * 60 + min;
	const nowMinutes = now.getHours() * 60 + now.getMinutes();
	if (nowMinutes < eventMinutes - 15) return 'before';
	if (nowMinutes <= eventMinutes + 60) return 'during';
	return 'after';
}
