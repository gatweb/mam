<script lang="ts">
	import { onMount } from 'svelte';
	import { API } from '$lib/store';

	let household = $state({ display_name: '', reassurance_message: '' });
	let faqs = $state<Array<{ id: number; question: string; answer: string }>>([]);
	let events = $state<Array<{ id: number; title: string; event_date: string; event_time: string | null; recurrence: string | null; recurrence_end: string | null; message_before: string | null }>>([]);
	let people = $state<Array<{ id: number; first_name: string; relation: string; message: string | null; next_visit: string | null; photo_path: string | null; is_primary_caregiver: boolean; allow_video_call: boolean }>>([]);

	let quickMsg = $state({ content: '', author: 'Gaëtan' });
	let dailyMessages = $state<Array<{ id: number; content: string; author: string | null; created_at: string }>>([]);
	let editingMsgId = $state<number | null>(null);
	let editingMsg = $state({ content: '', author: '' });
	const DAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
	let selectedDays = $state<boolean[]>([false, false, false, false, false, false, false]);
	let recurrenceType = $state<'none' | 'daily' | 'weekly' | 'monthly'>('none');
	let monthlyDay = $state(1);
	let recurrenceEnd = $state('');

	function buildRecurrence(): string {
		if (recurrenceType === 'none') return 'none';
		if (recurrenceType === 'daily') return 'daily';
		if (recurrenceType === 'weekly') {
			const days = selectedDays.map((on, i) => on ? i : -1).filter(i => i >= 0);
			return days.length ? `weekly:${days.join(',')}` : 'none';
		}
		if (recurrenceType === 'monthly') return `monthly:${monthlyDay}`;
		return 'none';
	}

	let newEvent = $state({ title: '', event_date: new Date().toISOString().slice(0, 10), event_time: '', person_name: '', message_before: '', message_during: '', message_after: '' });
	let newFaq = $state({ question: '', answer: '' });
	let newPerson = $state({ first_name: '', relation: '', message: '', birth_date: '', is_primary_caregiver: false, allow_video_call: false });
	let callingPersonId = $state<number | null>(null);
	let photos = $state<Array<{ id: number; path: string; caption: string | null; display_order: number }>>([]);
	let uploadingPhotos = $state(false);
	let editingCaptionId = $state<number | null>(null);
	let editingCaption = $state('');

	let settings = $state({
		ntfy_url: 'https://ntfy.sh',
		ntfy_topic: '',
		ntfy_token: '',
		daily_reminder_enabled: false,
		daily_reminder_time: '09:00',
		daily_reminder_message: '',
		night_start: '21:30',
		night_end: '07:00',
		ha_url: '',
		ha_token: '',
		latitude: 48.8566,
		longitude: 2.3522,
		alarm_enabled: false,
		alarm_time: '08:00',
		alarm_days: '0,1,2,3,4,5,6',
		alarm_ha_media_player: '',
		alarm_music_url: '',
		ha_position: 'bottom',
		jitsi_url: 'https://meet.jit.si',
		fall_webhook_token: '',
	});
	let fallbackAudios = $state<Array<{ name: string; url: string }>>([]);
	let uploadingAudio = $state(false);
	let triggeringAlarm = $state(false);
	let playingMusic = $state(false);
	let downloadingBackup = $state(false);
	let editingPersonId = $state<number | null>(null);
	let editingPerson = $state({ first_name: '', relation: '', message: '', next_visit: '', birth_date: '', is_primary_caregiver: false, allow_video_call: false });
	let restoringBackup = $state(false);
	let testingNotif = $state(false);
	let editingEventId = $state<number | null>(null);
	let editingEvent = $state({ title: '', event_date: '', event_time: '', recurrence: 'none', recurrence_end: '', message_before: '', message_during: '', message_after: '' });
	let editingFaqId = $state<number | null>(null);
	let editingFaq = $state({ question: '', answer: '' });
	let testingHa = $state(false);
	let haEntities = $state<Array<{ id: number; entity_id: string; label: string; icon: string; unit: string; state_on_label?: string | null; state_off_label?: string | null }>>([]);
	let newHaEntity = $state({ entity_id: '', label: '', icon: '🌡️', unit: '', state_on_label: '', state_off_label: '', state_on_color: '', state_off_color: '' });
	let showBinaryOptions = $state(false);
	let haSearch = $state('');
	let haSearchResults = $state<Array<{ entity_id: string; friendly_name: string; state: string; unit: string }>>([]);
	let haSearching = $state(false);

	let toast = $state('');
	let activeTab = $state('message');

	async function load() {
		const [h, f, e, p, st, ha, ph, msgs, audios] = await Promise.all([
			fetch(`${API}/api/household`).then(r => r.json()),
			fetch(`${API}/api/faqs`).then(r => r.json()),
			fetch(`${API}/api/events`).then(r => r.json()),
			fetch(`${API}/api/people`).then(r => r.json()),
			fetch(`${API}/api/settings`).then(r => r.json()),
			fetch(`${API}/api/ha/entities`).then(r => r.json()),
			fetch(`${API}/api/photos`).then(r => r.json()),
			fetch(`${API}/api/daily-messages`).then(r => r.json()),
			fetch(`${API}/api/audio/fallback`).then(r => r.json()).catch(() => []),
		]);
		household = h || household;
		faqs = f;
		events = e;
		people = p;
		if (st) settings = { ...settings, ...st };
		haEntities = ha;
		photos = ph;
		dailyMessages = msgs;
		fallbackAudios = audios;
	}

	// ── Sons de secours du réveil (joués si le flux radio échoue) ─────────
	async function uploadFallbackAudio(e: Event) {
		const input = e.target as HTMLInputElement;
		const files = Array.from(input.files ?? []);
		if (!files.length) return;
		uploadingAudio = true;
		try {
			for (const file of files) {
				const form = new FormData();
				form.append('file', file);
				const res = await fetch(`${API}/api/audio/fallback`, { method: 'POST', body: form });
				if (!res.ok) { const err = await res.json(); showToast(`Erreur : ${err.detail}`); return; }
			}
			await load();
			showToast('Son de secours ajouté ✓');
		} finally {
			uploadingAudio = false;
			input.value = '';
		}
	}

	async function deleteFallbackAudio(name: string) {
		await fetch(`${API}/api/audio/fallback/${encodeURIComponent(name)}`, { method: 'DELETE' });
		await load();
	}

	// ── Alerte chute : jeton secret pour l'automatisation Home Assistant ──
	function generateFallToken() {
		const bytes = new Uint8Array(24);
		crypto.getRandomValues(bytes);
		settings.fall_webhook_token = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
		saveSettings();
	}

	async function copyFallToken() {
		await navigator.clipboard.writeText(settings.fall_webhook_token);
		showToast('Jeton copié ✓');
	}

	async function testFallAlert() {
		const res = await fetch(`${API}/api/alert/fall`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ token: settings.fall_webhook_token, source: 'test depuis l\'admin' }),
		});
		if (res.ok) showToast('🚨 Alerte test déclenchée — regardez l\'écran et votre téléphone');
		else { const err = await res.json(); showToast(`Erreur : ${err.detail}`); }
	}

	async function saveSettings() {
		await fetch(`${API}/api/settings`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(settings),
		});
		showToast('Paramètres enregistrés ✓');
	}

	async function uploadPhotos(e: Event) {
		const input = e.target as HTMLInputElement;
		const files = Array.from(input.files ?? []);
		if (!files.length) return;
		uploadingPhotos = true;
		try {
			for (const file of files) {
				const form = new FormData();
				form.append('file', file);
				await fetch(`${API}/api/photos`, { method: 'POST', body: form });
			}
			await load();
			showToast(`${files.length} photo(s) ajoutée(s) ✓`);
		} finally {
			uploadingPhotos = false;
			input.value = '';
		}
	}

	async function deletePhoto(id: number) {
		await fetch(`${API}/api/photos/${id}`, { method: 'DELETE' });
		await load();
	}

	async function saveCaption(id: number) {
		await fetch(`${API}/api/photos/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ caption: editingCaption }),
		});
		editingCaptionId = null;
		await load();
	}

	const ALARM_DAYS_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

	function alarmDayActive(i: number): boolean {
		return (settings.alarm_days || '').split(',').includes(String(i));
	}

	function toggleAlarmDay(i: number) {
		const days = new Set((settings.alarm_days || '').split(',').filter(Boolean).map(Number));
		days.has(i) ? days.delete(i) : days.add(i);
		settings.alarm_days = [...days].sort().join(',') || '';
	}

	async function triggerAlarm() {
		triggeringAlarm = true;
		try {
			await fetch(`${API}/api/alarm/trigger`, { method: 'POST' });
			showToast('Réveil déclenché sur l\'écran ✓');
		} finally {
			triggeringAlarm = false;
		}
	}

	async function stopAlarm() {
		await fetch(`${API}/api/alarm/stop`, { method: 'POST' });
		showToast('Réveil arrêté ✓');
	}

	async function playMusic() {
		playingMusic = true;
		try {
			const res = await fetch(`${API}/api/music/play`, { method: 'POST' });
			if (res.ok) showToast('Musique lancée sur l\'écran ✓');
			else { const e = await res.json(); showToast(`Erreur : ${e.detail}`); }
		} finally {
			playingMusic = false;
		}
	}

	async function stopMusic() {
		await fetch(`${API}/api/music/stop`, { method: 'POST' });
		showToast('Musique arrêtée ✓');
	}

	function startEditPerson(p: typeof people[0]) {
		editingPersonId = p.id;
		editingPerson = {
			first_name: p.first_name,
			relation: p.relation,
			message: p.message ?? '',
			next_visit: p.next_visit ?? '',
			birth_date: (p as any).birth_date ?? '',
			is_primary_caregiver: p.is_primary_caregiver,
			allow_video_call: p.allow_video_call,
		};
	}

	async function savePerson() {
		if (!editingPersonId) return;
		await fetch(`${API}/api/people/${editingPersonId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(editingPerson),
		});
		editingPersonId = null;
		await load();
		showToast('Proche modifié ✓');
	}

	async function downloadBackup() {
		downloadingBackup = true;
		try {
			const res = await fetch(`${API}/api/backup`);
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `snoozolene-backup-${new Date().toISOString().slice(0, 10)}.zip`;
			a.click();
			URL.revokeObjectURL(url);
			showToast('Sauvegarde téléchargée ✓');
		} finally {
			downloadingBackup = false;
		}
	}

	async function testHaConnection() {
		testingHa = true;
		try {
			const res = await fetch(`${API}/api/ha/test`, { method: 'POST' });
			if (res.ok) showToast('Home Assistant connecté ✓');
			else {
				const err = await res.json();
				showToast(`Échec : ${err.detail}`);
			}
		} finally {
			testingHa = false;
		}
	}

	async function searchHaEntities() {
		if (!haSearch.trim()) return;
		haSearching = true;
		try {
			const res = await fetch(`${API}/api/ha/search?q=${encodeURIComponent(haSearch)}`);
			haSearchResults = res.ok ? await res.json() : [];
		} finally {
			haSearching = false;
		}
	}

	function pickHaEntity(result: typeof haSearchResults[0]) {
		newHaEntity.entity_id = result.entity_id;
		newHaEntity.label = result.friendly_name || result.entity_id;
		newHaEntity.unit = result.unit;
		// icône auto selon domaine
		const domain = result.entity_id.split('.')[0];
		const icons: Record<string, string> = {
			sensor: '📊', weather: '🌤️', binary_sensor: '🔵',
			device_tracker: '📍', climate: '🌡️', light: '💡',
			switch: '🔌', camera: '📷', cover: '🪟',
		};
		newHaEntity.icon = icons[domain] ?? '📊';
		haSearchResults = [];
		haSearch = '';
	}

	async function addHaEntity() {
		if (!newHaEntity.entity_id.trim()) return;
		await fetch(`${API}/api/ha/entities`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				...newHaEntity,
				// champs on/off vides → null (affichage par défaut Ouvert/Fermé)
				state_on_label: newHaEntity.state_on_label || null,
				state_off_label: newHaEntity.state_off_label || null,
				state_on_color: newHaEntity.state_on_color || null,
				state_off_color: newHaEntity.state_off_color || null,
				display_order: haEntities.length,
			}),
		});
		newHaEntity = { entity_id: '', label: '', icon: '🌡️', unit: '', state_on_label: '', state_off_label: '', state_on_color: '', state_off_color: '' };
		showBinaryOptions = false;
		await load();
		showToast('Entité ajoutée ✓');
	}

	async function deleteHaEntity(id: number) {
		await fetch(`${API}/api/ha/entities/${id}`, { method: 'DELETE' });
		await load();
	}

	async function testNotification() {
		testingNotif = true;
		try {
			const res = await fetch(`${API}/api/settings/test-notification`, { method: 'POST' });
			if (res.ok) showToast('Notification envoyée ✓ — vérifiez votre téléphone');
			else showToast('Échec — vérifiez le topic ntfy');
		} finally {
			testingNotif = false;
		}
	}

	function showToast(msg: string) {
		toast = msg;
		setTimeout(() => toast = '', 3000);
	}

	async function sendQuickMessage() {
		await fetch(`${API}/api/daily-message`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(quickMsg),
		});
		quickMsg.content = '';
		await load();
		showToast('Message envoyé à l\'écran ✓');
	}

	function startEditMsg(m: typeof dailyMessages[0]) {
		editingMsgId = m.id;
		editingMsg = { content: m.content, author: m.author ?? '' };
	}

	async function saveMsg() {
		if (!editingMsgId) return;
		await fetch(`${API}/api/daily-message/${editingMsgId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(editingMsg),
		});
		editingMsgId = null;
		await load();
		showToast('Message modifié ✓');
	}

	async function deleteMsg(id: number) {
		await fetch(`${API}/api/daily-message/${id}`, { method: 'DELETE' });
		await load();
		showToast('Message supprimé ✓');
	}

	async function saveHousehold() {
		await fetch(`${API}/api/household`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(household),
		});
		showToast('Maison mise à jour ✓');
	}

	async function addEvent() {
		const rec = buildRecurrence();
		await fetch(`${API}/api/events`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				...newEvent,
				recurrence: rec,
				recurrence_end: recurrenceEnd || null,
			}),
		});
		newEvent = { title: '', event_date: new Date().toISOString().slice(0, 10), event_time: '', person_name: '', message_before: '', message_during: '', message_after: '' };
		recurrenceType = 'none';
		selectedDays = [false, false, false, false, false, false, false];
		recurrenceEnd = '';
		await load();
		showToast('Événement ajouté ✓');
	}

	async function deleteEvent(id: number) {
		await fetch(`${API}/api/events/${id}`, { method: 'DELETE' });
		await load();
	}

	async function addFaq() {
		await fetch(`${API}/api/faqs`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(newFaq),
		});
		newFaq = { question: '', answer: '' };
		await load();
		showToast('Carte Q/R ajoutée ✓');
	}

	async function deleteFaq(id: number) {
		await fetch(`${API}/api/faqs/${id}`, { method: 'DELETE' });
		await load();
	}

	let pendingPhoto = $state<File | null>(null);
	let photoPreview = $state<string | null>(null);
	let uploadingFor = $state<number | null>(null);

	function onPhotoSelected(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		pendingPhoto = file;
		photoPreview = URL.createObjectURL(file);
	}

	async function uploadPhotoForPerson(personId: number) {
		if (!pendingPhoto) return;
		uploadingFor = personId;
		const form = new FormData();
		form.append('file', pendingPhoto);
		const res = await fetch(`${API}/api/upload/photo`, { method: 'POST', body: form });
		const { path } = await res.json();
		await fetch(`${API}/api/people/${personId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ photo_path: path }),
		});
		pendingPhoto = null;
		photoPreview = null;
		uploadingFor = null;
		await load();
		showToast('Photo ajoutée ✓');
	}

	async function addPerson() {
		const res = await fetch(`${API}/api/people`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(newPerson),
		});
		const created = await res.json();
		// Si une photo était sélectionnée, on l'attache immédiatement
		if (pendingPhoto) {
			await uploadPhotoForPerson(created.id);
		}
		newPerson = { first_name: '', relation: '', message: '', birth_date: '', is_primary_caregiver: false, allow_video_call: false };
		await load();
		showToast('Proche ajouté ✓');
	}

	async function deletePerson(id: number) {
		await fetch(`${API}/api/people/${id}`, { method: 'DELETE' });
		await load();
	}

	async function toggleVideoCall(person: typeof people[0]) {
		await fetch(`${API}/api/people/${person.id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ allow_video_call: !person.allow_video_call }),
		});
		await load();
	}

	async function startVideoCall(personId: number) {
		callingPersonId = personId;
		try {
			const res = await fetch(`${API}/api/video-call/start`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ person_id: personId }),
			});
			const { url } = await res.json();
			window.open(url, '_blank');
			showToast('Appel lancé — Jitsi ouvert dans un nouvel onglet');
		} finally {
			callingPersonId = null;
		}
	}

	async function endVideoCall() {
		try {
			await fetch(`${API}/api/video-call/end`, {
				method: 'POST'
			});
			showToast("Signal de fin d'appel envoyé à l'écran");
		} catch (e) {
			showToast("Erreur lors de la coupure de l'appel");
		}
	}

	async function restoreBackup(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		if (!confirm(`Restaurer la sauvegarde "${file.name}" ? Les données actuelles seront remplacées.`)) {
			input.value = '';
			return;
		}
		restoringBackup = true;
		try {
			const form = new FormData();
			form.append('file', file);
			const res = await fetch(`${API}/api/restore`, { method: 'POST', body: form });
			if (res.ok) {
				showToast('Sauvegarde restaurée ✓ — rechargez la page');
				setTimeout(() => location.reload(), 2000);
			} else {
				const err = await res.json();
				showToast(`Erreur : ${err.detail}`);
			}
		} finally {
			restoringBackup = false;
			input.value = '';
		}
	}

	function startEditEvent(ev: typeof events[0]) {
		editingEventId = ev.id;
		editingEvent = {
			title: ev.title,
			event_date: ev.event_date,
			event_time: ev.event_time ?? '',
			recurrence: ev.recurrence ?? 'none',
			recurrence_end: (ev as any).recurrence_end ?? '',
			message_before: (ev as any).message_before ?? '',
			message_during: (ev as any).message_during ?? '',
			message_after: (ev as any).message_after ?? '',
		};
	}

	async function saveEvent() {
		if (!editingEventId) return;
		await fetch(`${API}/api/events/${editingEventId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(editingEvent),
		});
		editingEventId = null;
		await load();
		showToast('Événement modifié ✓');
	}

	function startEditFaq(f: typeof faqs[0]) {
		editingFaqId = f.id;
		editingFaq = { question: f.question, answer: f.answer };
	}

	async function saveFaq() {
		if (!editingFaqId) return;
		await fetch(`${API}/api/faqs/${editingFaqId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(editingFaq),
		});
		editingFaqId = null;
		await load();
		showToast('Carte Q/R modifiée ✓');
	}

	async function resetSeed() {
		if (!confirm('Remettre toutes les données de démonstration ? (les données actuelles seront effacées)')) return;
		await fetch(`${API}/api/admin/reset-seed`, { method: 'POST' });
		await load();
		showToast('Données de démo rechargées ✓');
	}

	onMount(load);
</script>

<svelte:head><title>Snoozolène — Admin</title></svelte:head>

{#if toast}
	<div class="toast">{toast}</div>
{/if}

<div class="admin">
	<header>
		<h1>🏠 Snoozolène — Panneau aidant</h1>
		<a href="/display" target="_blank" class="preview-btn">Voir l'écran →</a>
	</header>

	<nav class="tabs">
		{#each [['message','✉️ Message'], ['agenda','📅 Agenda'], ['faq','💬 Questions'], ['proches','👨‍👩‍👧 Proches'], ['photos','📸 Photos'], ['notifs','🔔 Alertes'], ['maison','🏠 Maison']] as [tab, label]}
			<button class:active={activeTab === tab} onclick={() => activeTab = tab}>{label}</button>
		{/each}
	</nav>

	{#if activeTab === 'message'}
		<section class="card">
			<h2>Nouveau message</h2>
			<p class="hint">Apparaît sur l'écran en quelques secondes.</p>
			<textarea bind:value={quickMsg.content} rows="4" placeholder="Je suis allé faire les courses. Je reviens vers 17h. Tout va bien."></textarea>
			<input type="text" bind:value={quickMsg.author} placeholder="Ton prénom (ex: Gaëtan)" />
			<button class="primary" onclick={sendQuickMessage} disabled={!quickMsg.content.trim()}>
				Envoyer maintenant
			</button>
		</section>

		<section class="card">
			<h2>Messages envoyés</h2>
			{#if dailyMessages.length === 0}
				<p class="empty">Aucun message.</p>
			{:else}
				<ul class="list">
					{#each dailyMessages as m}
						<li class="event-li">
							{#if editingMsgId === m.id}
								<div class="inline-edit">
									<textarea bind:value={editingMsg.content} rows="3"></textarea>
									<input type="text" bind:value={editingMsg.author} placeholder="Auteur" />
									<div class="inline-edit-actions">
										<button class="btn-save-caption" onclick={saveMsg}>Enregistrer</button>
										<button class="btn-cancel-caption" onclick={() => editingMsgId = null}>Annuler</button>
									</div>
								</div>
							{:else}
								<div class="event-info">
									<p style="margin:0;white-space:pre-wrap">{m.content}</p>
									{#if m.author}<span class="daily-author-tag">— {m.author}</span>{/if}
									<div class="event-meta">{new Date(m.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</div>
								</div>
								<div class="item-actions">
									<button class="btn-edit" onclick={() => startEditMsg(m)}>✏️</button>
									<button class="del" onclick={() => deleteMsg(m.id)}>✕</button>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'agenda'}
		<section class="card">
			<h2>Ajouter un événement</h2>

			<input type="text" bind:value={newEvent.title} placeholder="Ex : Kiné Marc" />

			<!-- Récurrence -->
			<label class="field-label">Récurrence</label>
			<div class="rec-buttons">
				{#each [['none','Une fois'], ['daily','Tous les jours'], ['weekly','Certains jours'], ['monthly','Chaque mois']] as [val, label]}
					<button
						type="button"
						class="rec-btn"
						class:active={recurrenceType === val}
						onclick={() => recurrenceType = val as typeof recurrenceType}
					>{label}</button>
				{/each}
			</div>

			{#if recurrenceType === 'none'}
				<!-- Date unique -->
				<div class="row">
					<input type="date" bind:value={newEvent.event_date} />
					<input type="time" bind:value={newEvent.event_time} />
				</div>
			{:else if recurrenceType === 'weekly'}
				<div class="days-grid">
					{#each DAYS as day, i}
						<button
							type="button"
							class="day-btn"
							class:active={selectedDays[i]}
							onclick={() => selectedDays[i] = !selectedDays[i]}
						>{day}</button>
					{/each}
				</div>
				<div class="row">
					<div>
						<label class="field-label">À partir du</label>
						<input type="date" bind:value={newEvent.event_date} />
					</div>
					<div>
						<label class="field-label">Heure</label>
						<input type="time" bind:value={newEvent.event_time} />
					</div>
				</div>
				<label class="field-label">Jusqu'au (optionnel)</label>
				<input type="date" bind:value={recurrenceEnd} placeholder="Laisser vide = sans fin" />
			{:else if recurrenceType === 'daily'}
				<div class="row">
					<div>
						<label class="field-label">À partir du</label>
						<input type="date" bind:value={newEvent.event_date} />
					</div>
					<div>
						<label class="field-label">Heure</label>
						<input type="time" bind:value={newEvent.event_time} />
					</div>
				</div>
				<label class="field-label">Jusqu'au (optionnel)</label>
				<input type="date" bind:value={recurrenceEnd} />
			{:else if recurrenceType === 'monthly'}
				<label class="field-label">Jour du mois</label>
				<input type="number" bind:value={monthlyDay} min="1" max="28" />
				<div class="row">
					<div>
						<label class="field-label">À partir du</label>
						<input type="date" bind:value={newEvent.event_date} />
					</div>
					<div>
						<label class="field-label">Heure</label>
						<input type="time" bind:value={newEvent.event_time} />
					</div>
				</div>
			{/if}

			<label class="field-label">Personne concernée (optionnel)</label>
			<input type="text" bind:value={newEvent.person_name} placeholder="ex: Infirmière, Sophie…" />
			<p class="hint" style="margin-top:-0.3rem">
				Si ce prénom correspond à un proche enregistré, il apparaîtra automatiquement
				comme « présent aujourd'hui » sur l'écran le jour du rendez-vous.
			</p>

			<!-- Messages contextuels -->
			<details class="messages-details">
				<summary>Messages contextuels (optionnel)</summary>
				<input type="text" bind:value={newEvent.message_before} placeholder="Avant : « Le kiné vient cet après-midi »" />
				<input type="text" bind:value={newEvent.message_during} placeholder="Pendant : « Le kiné est là ! »" />
				<input type="text" bind:value={newEvent.message_after} placeholder="Après : « Le kiné est passé. Tout va bien. »" />
			</details>

			<button class="primary" onclick={addEvent} disabled={!newEvent.title.trim()}>Ajouter</button>
		</section>

		<section class="card">
			<h2>Événements programmés</h2>
			{#if events.length === 0}
				<p class="empty">Aucun événement.</p>
			{:else}
				<ul class="list">
					{#each events as e}
						<li class="event-li">
							{#if editingEventId === e.id}
								<div class="inline-edit">
									<input type="text" bind:value={editingEvent.title} placeholder="Titre" />
									<div class="row">
										<input type="date" bind:value={editingEvent.event_date} />
										<input type="time" bind:value={editingEvent.event_time} />
									</div>
									<details class="messages-details">
										<summary>Messages contextuels</summary>
										<input type="text" bind:value={editingEvent.message_before} placeholder="Avant" />
										<input type="text" bind:value={editingEvent.message_during} placeholder="Pendant" />
										<input type="text" bind:value={editingEvent.message_after} placeholder="Après" />
									</details>
									<div class="inline-edit-actions">
										<button class="btn-save-caption" onclick={saveEvent}>Enregistrer</button>
										<button class="btn-cancel-caption" onclick={() => editingEventId = null}>Annuler</button>
									</div>
								</div>
							{:else}
								<div class="event-info">
									<strong>{e.title}</strong>
									{#if e.event_time}
										<span class="event-time"> à {e.event_time.replace(':', 'h')}</span>
									{/if}
									<div class="event-meta">
										{#if !e.recurrence || e.recurrence === 'none'}
											📅 {e.event_date}
										{:else if e.recurrence === 'daily'}
											🔁 Tous les jours
										{:else if e.recurrence?.startsWith('weekly:')}
											🔁 {e.recurrence.split(':')[1].split(',').map(d => DAYS[+d]).join(', ')}
										{:else if e.recurrence?.startsWith('monthly:')}
											🔁 Le {e.recurrence.split(':')[1]} du mois
										{/if}
										{#if (e as any).recurrence_end}
											<span class="rec-end"> · jusqu'au {(e as any).recurrence_end}</span>
										{/if}
									</div>
								</div>
								<div class="item-actions">
									<button class="btn-edit" onclick={() => startEditEvent(e)}>✏️</button>
									<button class="del" onclick={() => deleteEvent(e.id)}>✕</button>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'faq'}
		<section class="card">
			<h2>Ajouter une carte Q/R</h2>
			<input type="text" bind:value={newFaq.question} placeholder="Question (ex: Est-ce que je rentre chez moi ?)" />
			<textarea bind:value={newFaq.answer} rows="3" placeholder="Réponse rassurante..."></textarea>
			<button class="primary" onclick={addFaq} disabled={!newFaq.question.trim() || !newFaq.answer.trim()}>Ajouter</button>
		</section>

		<section class="card">
			<h2>Cartes existantes</h2>
			{#if faqs.length === 0}
				<p class="empty">Aucune carte.</p>
			{:else}
				<ul class="list">
					{#each faqs as f}
						<li class="event-li">
							{#if editingFaqId === f.id}
								<div class="inline-edit">
									<input type="text" bind:value={editingFaq.question} placeholder="Question" />
									<textarea bind:value={editingFaq.answer} rows="3" placeholder="Réponse rassurante…"></textarea>
									<div class="inline-edit-actions">
										<button class="btn-save-caption" onclick={saveFaq}>Enregistrer</button>
										<button class="btn-cancel-caption" onclick={() => editingFaqId = null}>Annuler</button>
									</div>
								</div>
							{:else}
								<div class="event-info">
									<strong>{f.question}</strong>
									<p>{f.answer}</p>
								</div>
								<div class="item-actions">
									<button class="btn-edit" onclick={() => startEditFaq(f)}>✏️</button>
									<button class="del" onclick={() => deleteFaq(f.id)}>✕</button>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'proches'}
		<section class="card">
			<h2>Ajouter un proche</h2>
			<div class="row">
				<input type="text" bind:value={newPerson.first_name} placeholder="Prénom" />
				<input type="text" bind:value={newPerson.relation} placeholder="Lien (ex: ton fils)" />
			</div>
			<textarea bind:value={newPerson.message} rows="2" placeholder="Message rassurant (ex: Je suis dans la maison ou au travail. Je reviens toujours.)"></textarea>
			<label class="field-label">Date de naissance (optionnel — pour les anniversaires)</label>
			<input type="date" bind:value={newPerson.birth_date} />
			<label class="checkbox">
				<input type="checkbox" bind:checked={newPerson.is_primary_caregiver} />
				Présent — affiché sur l'écran comme étant à la maison
			</label>
			<label class="checkbox">
				<input type="checkbox" bind:checked={newPerson.allow_video_call} />
				Autoriser les appels vidéo depuis l'admin
			</label>

			<!-- Sélection photo -->
			<label class="field-label">Photo (optionnel — peut être ajoutée après)</label>
			<label class="photo-upload-zone">
				{#if photoPreview}
					<img src={photoPreview} alt="aperçu" class="photo-preview" />
					<span class="photo-change">Changer la photo</span>
				{:else}
					<span class="photo-placeholder">📷 Choisir une photo</span>
				{/if}
				<input type="file" accept="image/*" onchange={onPhotoSelected} class="hidden-input" />
			</label>

			<button class="primary" onclick={addPerson} disabled={!newPerson.first_name.trim()}>Ajouter</button>
		</section>

		<section class="card">
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.5rem;">
				<h2 style="margin: 0;">Proches enregistrés</h2>
				<button class="btn-danger-small" onclick={endVideoCall}>⏹ Raccrocher l'appel</button>
			</div>
			{#if people.length === 0}
				<p class="empty">Aucun proche.</p>
			{:else}
				<ul class="people-list">
					{#each people as person}
						<li class="person-item">
							<!-- Photo -->
							<div class="person-avatar-wrap">
								{#if person.photo_path}
									<img src="{API}{person.photo_path}" alt={person.first_name} class="person-avatar" />
								{:else}
									<div class="person-avatar-empty">
										{person.first_name[0]}
									</div>
								{/if}
							</div>

							{#if editingPersonId === person.id}
								<!-- Édition inline -->
								<div class="inline-edit" style="flex:1">
									<div class="row">
										<input type="text" bind:value={editingPerson.first_name} placeholder="Prénom" />
										<input type="text" bind:value={editingPerson.relation} placeholder="Lien (ex: ton fils)" />
									</div>
									<input type="text" bind:value={editingPerson.message} placeholder="Message rassurant" />
									<input type="text" bind:value={editingPerson.next_visit} placeholder="Prochaine visite (ex: dimanche)" />
									<label class="field-label">Date de naissance</label>
									<input type="date" bind:value={editingPerson.birth_date} />
									<label class="checkbox">
										<input type="checkbox" bind:checked={editingPerson.is_primary_caregiver} />
										Présent à la maison (affiché sur l'écran)
									</label>
									<label class="checkbox">
										<input type="checkbox" bind:checked={editingPerson.allow_video_call} />
										Appels vidéo autorisés
									</label>
									<div class="inline-edit-actions">
										<button class="btn-save-caption" onclick={savePerson}>Enregistrer</button>
										<button class="btn-cancel-caption" onclick={() => editingPersonId = null}>Annuler</button>
									</div>
								</div>
							{:else}
								<!-- Info -->
								<div class="person-details">
									<strong>{person.first_name}</strong>
									{#if person.is_primary_caregiver}<span class="badge">✅ Présent</span>{/if}
									<div class="person-relation-text">{person.relation}</div>
									{#if (person as any).birth_date}
										<div class="person-visit">🎂 {new Date((person as any).birth_date + 'T12:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })}</div>
									{/if}
									{#if person.next_visit}
										<div class="person-visit">Prochaine visite : {person.next_visit}</div>
									{/if}
								</div>

								<!-- Actions -->
								<div class="person-actions">
									{#if person.allow_video_call}
										<button
											class="call-btn"
											onclick={() => startVideoCall(person.id)}
											disabled={callingPersonId === person.id}
											title="Lancer un appel vidéo"
										>
											{callingPersonId === person.id ? '…' : '📞'}
										</button>
									{/if}
									<button
										class="video-toggle"
										class:active={person.allow_video_call}
										onclick={() => toggleVideoCall(person)}
										title={person.allow_video_call ? 'Désactiver les appels vidéo' : 'Activer les appels vidéo'}
									>🎥</button>
									<label class="photo-btn" title="Changer la photo">
										📷
										<input
											type="file"
											accept="image/*"
											class="hidden-input"
											onchange={async (e) => {
												const f = (e.target as HTMLInputElement).files?.[0];
												if (!f) return;
												pendingPhoto = f;
												await uploadPhotoForPerson(person.id);
											}}
										/>
									</label>
									<button class="btn-edit" onclick={() => startEditPerson(person)} title="Modifier">✏️</button>
									<button class="del" onclick={() => deletePerson(person.id)} title="Supprimer">✕</button>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'photos'}
		<section class="card">
			<h2>Ajouter des photos</h2>
			<p class="hint">Les photos défilent en diaporama sur l'écran de Agnès. Vous pouvez en ajouter plusieurs à la fois.</p>
			<label class="photo-drop-zone" class:uploading={uploadingPhotos}>
				{#if uploadingPhotos}
					<span>Envoi en cours…</span>
				{:else}
					<span class="drop-icon">📸</span>
					<span>Cliquer ou glisser des photos ici</span>
					<span class="hint" style="margin:0">JPG, PNG, HEIC — plusieurs fichiers acceptés</span>
				{/if}
				<input type="file" accept="image/*" multiple onchange={uploadPhotos} class="hidden-input" />
			</label>
		</section>

		<section class="card">
			<h2>Album ({photos.length} photo{photos.length > 1 ? 's' : ''})</h2>
			{#if photos.length === 0}
				<p class="empty">Aucune photo dans l'album.</p>
			{:else}
				<div class="photo-grid">
					{#each photos as photo}
						<div class="photo-card">
							<img src="{API}{photo.path}" alt={photo.caption ?? ''} class="photo-thumb" />
							<div class="photo-card-body">
								{#if editingCaptionId === photo.id}
									<input
										type="text"
										bind:value={editingCaption}
										placeholder="Légende (ex: Gaëtan et Agnès, Noël 2023)"
										onkeydown={(e) => { if (e.key === 'Enter') saveCaption(photo.id); if (e.key === 'Escape') editingCaptionId = null; }}
										style="margin-bottom:0.4rem"
									/>
									<div class="photo-card-actions">
										<button class="btn-save-caption" onclick={() => saveCaption(photo.id)}>Enregistrer</button>
										<button class="btn-cancel-caption" onclick={() => editingCaptionId = null}>Annuler</button>
									</div>
								{:else}
									<span
										class="photo-caption"
										onclick={() => { editingCaptionId = photo.id; editingCaption = photo.caption ?? ''; }}
									>{photo.caption ?? '✏️ Ajouter une légende'}</span>
									<button class="del photo-del" onclick={() => deletePhoto(photo.id)} title="Supprimer">✕</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'notifs'}
		<section class="card">
			<h2>Notifications sur votre téléphone</h2>
			<p class="hint">
				Utilisez <strong>ntfy</strong> pour recevoir des alertes push gratuitement.
				Installez l'app <em>ntfy</em> sur votre téléphone, créez un topic unique (ex: <code>snoozolene-gaetan-2026</code>) et copiez-le ici.
			</p>

			<label class="field-label">URL du serveur ntfy</label>
			<input type="url" bind:value={settings.ntfy_url} placeholder="https://ntfy.sh" />

			<label class="field-label">Topic (identifiant unique de votre canal)</label>
			<input type="text" bind:value={settings.ntfy_topic} placeholder="ex: snoozolene-gaetan-2026" />

			<label class="field-label">Token d'accès (optionnel — pour topic privé)</label>
			<input type="password" bind:value={settings.ntfy_token} placeholder="Laisser vide si topic public" />

			<button
				class="btn-test"
				onclick={testNotification}
				disabled={!settings.ntfy_topic || testingNotif}
			>
				{testingNotif ? 'Envoi…' : '🔔 Envoyer une notification test'}
			</button>
		</section>

		<section class="card">
			<h2>Alertes automatiques</h2>

			<div class="setting-row">
				<div>
					<strong>Écran déconnecté</strong>
					<p class="hint">Alerte si l'écran patient se déconnecte plus de 60 secondes.</p>
				</div>
				<span class="badge-auto">Automatique</span>
			</div>

			<hr />

			<div class="setting-row">
				<div>
					<strong>Rappel quotidien aidant</strong>
					<p class="hint">Un rappel sur votre téléphone pour penser à mettre à jour le message du jour.</p>
				</div>
				<label class="toggle">
					<input type="checkbox" bind:checked={settings.daily_reminder_enabled} />
					<span class="slider"></span>
				</label>
			</div>

			{#if settings.daily_reminder_enabled}
				<label class="field-label">Heure du rappel</label>
				<input type="time" bind:value={settings.daily_reminder_time} />
				<label class="field-label">Message du rappel</label>
				<input type="text" bind:value={settings.daily_reminder_message} placeholder="N'oubliez pas de mettre à jour le message du jour." />
			{/if}
		</section>

		<section class="card">
			<h2>Heures du mode nuit</h2>
			<p class="hint">En mode nuit, l'écran n'affiche que l'heure et un message rassurant très simple.</p>
			<div class="row">
				<div>
					<label class="field-label">Début de nuit</label>
					<input type="time" bind:value={settings.night_start} />
				</div>
				<div>
					<label class="field-label">Fin de nuit (réveil)</label>
					<input type="time" bind:value={settings.night_end} />
				</div>
			</div>
			<button class="primary" onclick={saveSettings}>Enregistrer tout</button>
		</section>

		<section class="card">
			<h2>⏰ Réveil</h2>
			<p class="hint">Affiche un écran de réveil lumineux sur la tablette à l'heure choisie. Peut aussi lancer de la musique via Home Assistant.</p>

			<div class="setting-row">
				<div><strong>Activer le réveil</strong></div>
				<label class="toggle">
					<input type="checkbox" bind:checked={settings.alarm_enabled} />
					<span class="slider"></span>
				</label>
			</div>

			{#if settings.alarm_enabled}
				<label class="field-label">Heure du réveil</label>
				<input type="time" bind:value={settings.alarm_time} />

				<label class="field-label">Jours actifs</label>
				<div class="days-grid" style="margin-bottom:0.75rem">
					{#each ALARM_DAYS_LABELS as label, i}
						<button
							type="button"
							class="day-btn"
							class:active={alarmDayActive(i)}
							onclick={() => toggleAlarmDay(i)}
						>{label}</button>
					{/each}
				</div>

				<label class="field-label">Lecteur HA pour la musique (optionnel)</label>
				<input type="text" bind:value={settings.alarm_ha_media_player} placeholder="ex: media_player.salon" />

				<label class="field-label">URL de la musique / flux radio</label>
				<input type="url" bind:value={settings.alarm_music_url} placeholder="ex: https://stream.radio.fr/..." />
			{/if}

			<label class="field-label">Sons de secours (si la radio est injoignable)</label>
			<p class="hint" style="margin-top:0">
				Le réveil sonne <strong>toujours</strong>, même sans Internet : si le flux radio ne démarre pas
				en 8 secondes, un de ces fichiers est joué à la place. Sans fichier, un carillon doux intégré est utilisé.
			</p>
			{#if fallbackAudios.length > 0}
				<ul class="list">
					{#each fallbackAudios as audio}
						<li>
							<span>🎵 {audio.name}</span>
							<button class="del" onclick={() => deleteFallbackAudio(audio.name)}>✕</button>
						</li>
					{/each}
				</ul>
			{/if}
			<label class="btn-test" style="display:block;text-align:center;cursor:pointer">
				{uploadingAudio ? 'Envoi…' : '⬆️ Ajouter un fichier audio (mp3, wav…)'}
				<input type="file" accept="audio/*" multiple onchange={uploadFallbackAudio} class="hidden-input" disabled={uploadingAudio} />
			</label>

			<button class="primary" onclick={saveSettings}>Enregistrer</button>

			<div class="ha-btn-row" style="margin-top:0.5rem">
				<button class="btn-test" onclick={triggerAlarm} disabled={triggeringAlarm} style="flex:1">
					{triggeringAlarm ? '…' : '⏰ Tester le réveil maintenant'}
				</button>
				<button class="btn-danger-small" onclick={stopAlarm} style="flex:1">⏹ Arrêter</button>
			</div>
		</section>

		<section class="card">
			<h2>🎵 Musique</h2>
			<p class="hint">Lance ou arrête la musique sur l'écran d'Agnès (et sur Home Assistant si configuré). L'URL est celle configurée dans la section Réveil ci-dessus.</p>
			{#if !settings.alarm_music_url}
				<p class="hint" style="color:#e67e22">Ajoutez d'abord une URL de flux radio dans la section Réveil.</p>
			{/if}
			<div class="ha-btn-row">
				<button class="btn-test" onclick={playMusic} disabled={playingMusic || !settings.alarm_music_url} style="flex:1">
					{playingMusic ? '…' : '🎵 Lancer la musique'}
				</button>
				<button class="btn-danger-small" onclick={stopMusic} disabled={!settings.alarm_music_url} style="flex:1">⏹ Arrêter</button>
			</div>
		</section>

		<section class="card">
			<h2>📞 Appels vidéo (Jitsi)</h2>
			<p class="hint">
				Serveur utilisé pour les appels vidéo. Le serveur public <code>meet.jit.si</code> exige
				désormais un organisateur connecté (Google/GitHub) — l'écran peut rester bloqué sur
				« en attente de l'organisateur ». Pour un appel <strong>100 % automatique</strong>,
				hébergez votre propre serveur : voir <code>docs/appels-video.md</code> du projet.
			</p>
			<label class="field-label">URL du serveur Jitsi</label>
			<input type="url" bind:value={settings.jitsi_url} placeholder="https://meet.jit.si" />
			<button class="primary" onclick={saveSettings}>Enregistrer</button>
		</section>

		<section class="card">
			<h2>🚨 Alerte chute</h2>
			<p class="hint">
				Une automatisation Home Assistant (ex : détection de chute du capteur Aqara FP2) peut
				déclencher un <strong>appel vidéo automatique</strong> sur l'écran + une notification
				urgente sur votre téléphone. Générez un jeton, puis suivez <code>docs/detection-chute.md</code>.
			</p>
			<label class="field-label">Jeton secret (à copier dans l'automatisation HA)</label>
			<div class="row">
				<input type="text" readonly value={settings.fall_webhook_token} placeholder="Aucun jeton — alerte désactivée" style="flex:3" />
				<button class="btn-test" onclick={generateFallToken} style="flex:1">↻ Générer</button>
			</div>
			{#if settings.fall_webhook_token}
				<div class="ha-btn-row">
					<button class="btn-test" onclick={copyFallToken} style="flex:1">📋 Copier le jeton</button>
					<button class="btn-danger-small" onclick={testFallAlert} style="flex:1">🚨 Tester l'alerte</button>
				</div>
				<p class="hint" style="margin-top:0.5rem">
					L'automatisation doit appeler : <code>POST /api/alert/fall</code> avec
					<code>{'{'}"token": "…", "source": "salle de bain"{'}'}</code>
				</p>
			{/if}
		</section>

		<section class="card">
			<h2>🏠 Home Assistant</h2>
			<p class="hint">Affichez la température, la présence ou n'importe quel capteur HA sur l'écran de Agnès.</p>

			<label class="field-label">URL de votre instance HA</label>
			<input type="url" bind:value={settings.ha_url} placeholder="http://192.168.0.100:8123" />

			<label class="field-label">Long-Lived Access Token</label>
			<input type="password" bind:value={settings.ha_token} placeholder="Profil HA → Sécurité → Tokens d'accès longue durée" />

			<div class="ha-btn-row">
				<button class="primary" onclick={saveSettings} style="flex:1">Enregistrer</button>
				<button
					class="btn-test"
					onclick={testHaConnection}
					disabled={!settings.ha_url || !settings.ha_token || testingHa}
					style="flex:1"
				>{testingHa ? 'Test…' : '🔗 Tester la connexion'}</button>
			</div>
		</section>

		<section class="card">
			<h2>Capteurs affichés sur l'écran</h2>
			<div class="setting-row" style="margin-bottom:0.75rem">
				<div>
					<strong>Position des capteurs</strong>
					<p class="hint">En haut (dans la barre météo) ou en bas de l'écran.</p>
				</div>
				<div class="pos-toggle">
					<button
						class="pos-btn"
						class:active={settings.ha_position === 'top'}
						onclick={() => { settings.ha_position = 'top'; saveSettings(); }}
					>⬆ Haut</button>
					<button
						class="pos-btn"
						class:active={settings.ha_position === 'bottom'}
						onclick={() => { settings.ha_position = 'bottom'; saveSettings(); }}
					>⬇ Bas</button>
				</div>
			</div>

			<!-- Recherche d'entités -->
			<label class="field-label">Rechercher une entité HA</label>
			<div class="row">
				<input
					type="text"
					bind:value={haSearch}
					placeholder="ex: temperature, gaetan, salon…"
					onkeydown={(e) => e.key === 'Enter' && searchHaEntities()}
				/>
				<button class="btn-search" onclick={searchHaEntities} disabled={haSearching || !settings.ha_url}>
					{haSearching ? '…' : '🔍'}
				</button>
			</div>

			{#if haSearchResults.length > 0}
				<ul class="ha-results">
					{#each haSearchResults as result}
						<li onclick={() => pickHaEntity(result)} class="ha-result-item">
							<span class="ha-entity-id">{result.entity_id}</span>
							{#if result.friendly_name}
								<span class="ha-friendly">{result.friendly_name}</span>
							{/if}
							<span class="ha-state-preview">{result.state}{result.unit}</span>
						</li>
					{/each}
				</ul>
			{/if}

			<!-- Formulaire d'ajout manuel ou après sélection -->
			<div class="ha-add-form">
				<div class="row">
					<input type="text" bind:value={newHaEntity.entity_id} placeholder="entity_id (ex: sensor.temp_salon)" style="flex:3" />
					<input type="text" bind:value={newHaEntity.icon} placeholder="🌡️" style="flex:0.5; text-align:center" />
				</div>
				<div class="row">
					<input type="text" bind:value={newHaEntity.label} placeholder="Libellé (ex: Salon)" style="flex:3" />
					<input type="text" bind:value={newHaEntity.unit} placeholder="°C" style="flex:0.8" />
				</div>

				<!-- Capteurs binaires (portes, présence FP2…) : textes clairs plutôt que « Ouvert/Fermé » -->
				<details class="messages-details" bind:open={showBinaryOptions}>
					<summary>Affichage personnalisé on/off (capteurs de présence, portes…)</summary>
					<p class="hint">
						Ex. capteur de présence FP2 dans la salle de bain :
						détecté → « Salle de bain occupée » en rouge, sinon « Salle de bain libre » en vert.
					</p>
					<div class="row">
						<input type="text" bind:value={newHaEntity.state_on_label} placeholder="Si détecté/on (ex: Salle de bain occupée)" style="flex:3" />
						<input type="color" bind:value={newHaEntity.state_on_color} style="flex:0.5; min-width:48px; padding:2px; height:38px" title="Couleur si on" />
					</div>
					<div class="row">
						<input type="text" bind:value={newHaEntity.state_off_label} placeholder="Si vide/off (ex: Salle de bain libre)" style="flex:3" />
						<input type="color" bind:value={newHaEntity.state_off_color} style="flex:0.5; min-width:48px; padding:2px; height:38px" title="Couleur si off" />
					</div>
					<div class="ha-btn-row">
						<button type="button" class="btn-test" style="flex:1" onclick={() => {
							newHaEntity.state_on_label = newHaEntity.state_on_label || 'Salle de bain occupée';
							newHaEntity.state_off_label = newHaEntity.state_off_label || 'Salle de bain libre';
							newHaEntity.state_on_color = '#f87171';
							newHaEntity.state_off_color = '#4ade80';
						}}>🚿 Pré-remplir « salle de bain »</button>
					</div>
				</details>

				<button class="primary" onclick={addHaEntity} disabled={!newHaEntity.entity_id.trim()}>Ajouter à l'écran</button>
			</div>

			<!-- Liste des entités configurées -->
			{#if haEntities.length > 0}
				<ul class="list" style="margin-top:0.75rem">
					{#each haEntities as ent}
						<li>
							<div>
								<strong>{ent.icon} {ent.label}</strong>
								<div class="event-meta">
									{ent.entity_id}{ent.unit ? ` · ${ent.unit}` : ''}
									{#if ent.state_on_label || ent.state_off_label}
										· on : « {ent.state_on_label ?? 'Ouvert'} » / off : « {ent.state_off_label ?? 'Fermé'} »
									{/if}
								</div>
							</div>
							<button class="del" onclick={() => deleteHaEntity(ent.id)}>✕</button>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="empty">Aucun capteur configuré.</p>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'maison'}
		<section class="card">
			<h2>Informations de la maison</h2>
			<label class="field-label">Nom affiché sur l'écran</label>
			<input type="text" bind:value={household.display_name} placeholder="ex: chez Gaëtan" />
			<label class="field-label">Message rassurant principal</label>
			<textarea bind:value={household.reassurance_message} rows="3" placeholder="Tu es chez Gaëtan, ton fils. Tu es en sécurité."></textarea>
			<button class="primary" onclick={saveHousehold}>Enregistrer</button>
		</section>

		<section class="card">
			<h2>🌤️ Météo</h2>
			<p class="hint">La météo de la semaine s'affiche sur l'écran. Entrez les coordonnées GPS de chez vous (Open-Meteo, gratuit, sans compte).</p>
			<div class="row">
				<div>
					<label class="field-label">Latitude</label>
					<input type="number" step="0.0001" bind:value={settings.latitude} placeholder="48.8566" />
				</div>
				<div>
					<label class="field-label">Longitude</label>
					<input type="number" step="0.0001" bind:value={settings.longitude} placeholder="2.3522" />
				</div>
			</div>
			<p class="hint" style="margin-top:-0.3rem">
				Trouvez vos coordonnées sur <strong>maps.google.com</strong> → clic droit sur votre adresse → copier les coordonnées.
			</p>
			<button class="primary" onclick={saveSettings}>Enregistrer</button>
		</section>

		<section class="card">
			<h2>💾 Sauvegarde</h2>
			<p class="hint">Télécharge un fichier ZIP contenant la base de données et toutes les photos. À faire avant chaque mise à jour.</p>
			<button class="btn-backup" onclick={downloadBackup} disabled={downloadingBackup}>
				{downloadingBackup ? 'Préparation…' : '💾 Télécharger la sauvegarde'}
			</button>
			<hr style="margin:1rem 0" />
			<p class="hint">Pour restaurer une sauvegarde, importez le fichier ZIP précédemment téléchargé. <strong>Attention : les données actuelles seront remplacées.</strong></p>
			<label class="btn-restore" class:restoring={restoringBackup}>
				{restoringBackup ? 'Restauration en cours…' : '📂 Importer une sauvegarde (.zip)'}
				<input type="file" accept=".zip" onchange={restoreBackup} class="hidden-input" disabled={restoringBackup} />
			</label>
		</section>

		<section class="card danger-zone">
			<h2>Données de démonstration</h2>
			<p class="hint">Recharge les exemples de départ (Agnès, Gaëtan, Sophie, événements et questions types). Les données actuelles seront effacées.</p>
			<button class="btn-danger" onclick={resetSeed}>↺ Remettre les données de démo</button>
		</section>
	{/if}
</div>

<style>
	:global(body) {
		margin: 0;
		font-family: system-ui, sans-serif;
		background: #f5f5f5;
		color: #1a1a1a;
	}

	.admin { max-width: 680px; margin: 0 auto; padding: 1rem; }

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 0;
	}

	header h1 { margin: 0; font-size: 1.3rem; }

	.preview-btn {
		background: #1a1a2e;
		color: #ffd700;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		text-decoration: none;
		font-weight: 600;
	}

	.tabs { display: flex; gap: 0.3rem; flex-wrap: wrap; margin-bottom: 1rem; }

	.tabs button {
		padding: 0.5rem 1rem;
		border: 2px solid #ddd;
		background: white;
		border-radius: 2rem;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.tabs button.active { background: #1a1a2e; color: white; border-color: #1a1a2e; }

	.card {
		background: white;
		border-radius: 1rem;
		padding: 1.5rem;
		margin-bottom: 1rem;
		box-shadow: 0 2px 8px rgba(0,0,0,0.06);
	}

	.card h2 { margin: 0 0 0.5rem; font-size: 1.1rem; }
	.hint { color: #666; font-size: 0.9rem; margin: 0 0 0.75rem; }

	input, textarea {
		width: 100%;
		padding: 0.75rem;
		border: 2px solid #e0e0e0;
		border-radius: 0.5rem;
		font-size: 1rem;
		box-sizing: border-box;
		margin-bottom: 0.75rem;
		font-family: inherit;
	}

	input:focus, textarea:focus { outline: none; border-color: #1a1a2e; }

	.row { display: flex; gap: 0.5rem; }
	.row input { flex: 1; }

	.primary {
		width: 100%;
		padding: 0.9rem;
		background: #1a1a2e;
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-size: 1.1rem;
		font-weight: 600;
		cursor: pointer;
	}

	.primary:disabled { opacity: 0.4; cursor: not-allowed; }

	.list { list-style: none; padding: 0; margin: 0; }

	.list li {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		padding: 0.75rem 0;
		border-bottom: 1px solid #eee;
	}

	.list li p { margin: 0.25rem 0 0; color: #555; font-size: 0.9rem; }

	.del {
		background: #fee;
		border: none;
		color: #c00;
		padding: 0.3rem 0.6rem;
		border-radius: 0.3rem;
		cursor: pointer;
		flex-shrink: 0;
	}

	.checkbox { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; }
	.checkbox input { width: auto; margin: 0; }

	.empty { color: #999; font-style: italic; }

	.field-label {
		display: block;
		font-size: 0.85rem;
		font-weight: 600;
		color: #555;
		margin-bottom: 0.3rem;
	}

	.rec-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-bottom: 0.75rem;
	}

	.rec-btn {
		padding: 0.4rem 0.9rem;
		border: 2px solid #ddd;
		background: white;
		border-radius: 2rem;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.rec-btn.active {
		background: #1a1a2e;
		color: white;
		border-color: #1a1a2e;
	}

	.days-grid {
		display: flex;
		gap: 0.4rem;
		margin-bottom: 0.75rem;
	}

	.day-btn {
		flex: 1;
		padding: 0.6rem 0;
		border: 2px solid #ddd;
		background: white;
		border-radius: 0.5rem;
		cursor: pointer;
		font-size: 0.85rem;
		font-weight: 600;
	}

	.day-btn.active {
		background: #ffd700;
		border-color: #e6c200;
		color: #1a1a2e;
	}

	.messages-details {
		margin-bottom: 0.75rem;
		border: 1px solid #eee;
		border-radius: 0.5rem;
		padding: 0.5rem 0.75rem;
	}

	.messages-details summary {
		cursor: pointer;
		font-size: 0.9rem;
		color: #555;
		padding: 0.3rem 0;
	}

	.messages-details input {
		margin-top: 0.5rem;
	}

	.event-time { color: #555; font-weight: 400; }
	.event-meta { font-size: 0.85rem; color: #777; margin-top: 0.2rem; }
	.rec-end { color: #999; }

	/* ── Upload photo ─────────────────────────────────────── */
	.hidden-input { display: none; }

	.photo-upload-zone {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		border: 2px dashed #ddd;
		border-radius: 0.75rem;
		padding: 1rem;
		cursor: pointer;
		margin-bottom: 0.75rem;
		transition: border-color 0.2s;
		min-height: 80px;
	}

	.photo-upload-zone:hover { border-color: #1a1a2e; }

	.photo-preview {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		object-fit: cover;
		border: 3px solid #ffd700;
		margin-bottom: 0.4rem;
	}

	.photo-placeholder { font-size: 1.1rem; color: #888; }
	.photo-change { font-size: 0.85rem; color: #555; }

	/* ── Liste proches ────────────────────────────────────── */
	.people-list { list-style: none; padding: 0; margin: 0; }

	.person-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 0;
		border-bottom: 1px solid #eee;
	}

	.person-avatar-wrap { flex-shrink: 0; }

	.person-avatar {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		object-fit: cover;
		border: 3px solid #ffd700;
	}

	.person-avatar-empty {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: #1a1a2e;
		color: #ffd700;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.5rem;
		font-weight: 700;
	}

	.person-details { flex: 1; min-width: 0; }
	.badge { background: #ffd700; color: #1a1a2e; font-size: 0.75rem; padding: 0.1rem 0.4rem; border-radius: 1rem; margin-left: 0.4rem; font-weight: 600; }
	.person-relation-text { font-size: 0.9rem; color: #555; }
	.person-visit { font-size: 0.8rem; color: #888; margin-top: 0.1rem; }

	.person-actions { display: flex; gap: 0.4rem; flex-shrink: 0; }

	.photo-btn {
		background: #f0f4ff;
		border: 1px solid #ddd;
		color: #444;
		padding: 0.4rem 0.6rem;
		border-radius: 0.4rem;
		cursor: pointer;
		font-size: 1rem;
	}

	.call-btn {
		background: #e8f5e9;
		border: 2px solid #2e7d32;
		color: #2e7d32;
		padding: 0.4rem 0.7rem;
		border-radius: 0.4rem;
		cursor: pointer;
		font-size: 1rem;
		font-weight: 700;
	}

	.call-btn:disabled { opacity: 0.5; cursor: not-allowed; }

	.video-toggle {
		background: #f5f5f5;
		border: 1px solid #ddd;
		color: #888;
		padding: 0.4rem 0.6rem;
		border-radius: 0.4rem;
		cursor: pointer;
		font-size: 1rem;
		opacity: 0.5;
	}

	.video-toggle.active {
		background: #e3f2fd;
		border-color: #1565c0;
		color: #1565c0;
		opacity: 1;
	}

	.btn-danger-small {
		padding: 0.9rem;
		background: white;
		color: #c00;
		border: 2px solid #c00;
		border-radius: 0.5rem;
		font-size: 0.95rem;
		font-weight: 600;
		cursor: pointer;
	}

	.btn-danger-small:hover { background: #fee; }

	.btn-backup {
		width: 100%;
		padding: 0.9rem;
		background: #e8f4e8;
		color: #1a4a1a;
		border: 2px solid #2e7d32;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
	}

	.btn-backup:hover:not(:disabled) { background: #d0ecd0; }
	.btn-backup:disabled { opacity: 0.5; cursor: not-allowed; }

	/* ── Zone danger ──────────────────────────────────────── */
	.danger-zone { border: 1px solid #fcc; }
	.danger-zone h2 { color: #c00; }

	.btn-danger {
		width: 100%;
		padding: 0.75rem;
		background: white;
		color: #c00;
		border: 2px solid #c00;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
	}

	.btn-danger:hover { background: #fee; }

	/* ── Notifications ────────────────────────────────────── */
	code {
		background: #f0f0f0;
		padding: 0.1rem 0.4rem;
		border-radius: 0.3rem;
		font-size: 0.85rem;
	}

	.btn-test {
		width: 100%;
		padding: 0.9rem;
		background: #e8f4e8;
		color: #1a6e1a;
		border: 2px solid #1a6e1a;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		margin-top: 0.25rem;
	}

	.btn-test:disabled { opacity: 0.5; cursor: not-allowed; }
	.btn-test:hover:not(:disabled) { background: #d0ecd0; }

	.setting-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		padding: 0.5rem 0;
	}

	.setting-row p { margin: 0.2rem 0 0; }

	.badge-auto {
		background: #e8f0fe;
		color: #1a4eb3;
		font-size: 0.78rem;
		font-weight: 600;
		padding: 0.2rem 0.6rem;
		border-radius: 1rem;
		white-space: nowrap;
	}

	hr { border: none; border-top: 1px solid #eee; margin: 0.75rem 0; }

	/* Toggle switch */
	.toggle { position: relative; display: inline-block; width: 48px; height: 26px; flex-shrink: 0; }
	.toggle input { opacity: 0; width: 0; height: 0; }
	.slider {
		position: absolute; inset: 0;
		background: #ccc;
		border-radius: 26px;
		cursor: pointer;
		transition: background 0.2s;
	}
	.slider::before {
		content: '';
		position: absolute;
		width: 20px; height: 20px;
		left: 3px; top: 3px;
		background: white;
		border-radius: 50%;
		transition: transform 0.2s;
	}
	.toggle input:checked + .slider { background: #1a6e1a; }
	.toggle input:checked + .slider::before { transform: translateX(22px); }

	/* ── Photos ──────────────────────────────────────────── */
	.photo-drop-zone {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		border: 2px dashed #ddd;
		border-radius: 0.75rem;
		padding: 2rem 1rem;
		cursor: pointer;
		text-align: center;
		transition: border-color 0.2s, background 0.2s;
		min-height: 120px;
	}

	.photo-drop-zone:hover { border-color: #1a1a2e; background: #f8f8ff; }
	.photo-drop-zone.uploading { opacity: 0.6; cursor: wait; }
	.drop-icon { font-size: 2.5rem; }

	.photo-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: 0.75rem;
	}

	.photo-card {
		border-radius: 0.75rem;
		overflow: hidden;
		border: 1px solid #eee;
		display: flex;
		flex-direction: column;
	}

	.photo-thumb {
		width: 100%;
		aspect-ratio: 1;
		object-fit: cover;
		display: block;
	}

	.photo-card-body {
		padding: 0.4rem 0.5rem;
		display: flex;
		align-items: center;
		gap: 0.3rem;
		min-height: 32px;
	}

	.photo-caption {
		flex: 1;
		font-size: 0.78rem;
		color: #666;
		cursor: pointer;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.photo-caption:hover { color: #1a1a2e; text-decoration: underline; }

	.photo-del {
		padding: 0.2rem 0.4rem;
		font-size: 0.75rem;
		flex-shrink: 0;
	}

	.photo-card-actions { display: flex; gap: 0.3rem; }

	.btn-save-caption {
		padding: 0.3rem 0.6rem;
		background: #1a1a2e;
		color: white;
		border: none;
		border-radius: 0.3rem;
		cursor: pointer;
		font-size: 0.8rem;
	}

	.btn-cancel-caption {
		padding: 0.3rem 0.6rem;
		background: #eee;
		border: none;
		border-radius: 0.3rem;
		cursor: pointer;
		font-size: 0.8rem;
	}

	/* ── Home Assistant ──────────────────────────────────── */
	.ha-btn-row { display: flex; gap: 0.5rem; margin-bottom: 0; }
	.ha-btn-row .primary, .ha-btn-row .btn-test { margin-bottom: 0; }

	.btn-search {
		padding: 0.75rem 1rem;
		background: #f0f0f0;
		border: 2px solid #ddd;
		border-radius: 0.5rem;
		cursor: pointer;
		font-size: 1.1rem;
		flex-shrink: 0;
	}

	.btn-search:disabled { opacity: 0.4; cursor: not-allowed; }

	.ha-results {
		list-style: none;
		padding: 0;
		margin: 0 0 0.75rem;
		border: 1px solid #e0e0e0;
		border-radius: 0.5rem;
		max-height: 220px;
		overflow-y: auto;
	}

	.ha-result-item {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		cursor: pointer;
		border-bottom: 1px solid #f0f0f0;
		flex-wrap: wrap;
	}

	.ha-result-item:hover { background: #f5f8ff; }
	.ha-result-item:last-child { border-bottom: none; }

	.ha-entity-id { font-size: 0.8rem; color: #888; font-family: monospace; }
	.ha-friendly { font-weight: 600; font-size: 0.95rem; }
	.ha-state-preview { margin-left: auto; font-size: 0.85rem; color: #1a4eb3; font-weight: 600; }

	.ha-add-form { margin-top: 0.5rem; }

	/* ── Inline editing ─────────────────────────────────── */
	.event-li {
		display: flex;
		flex-direction: column;
		padding: 0.75rem 0;
		border-bottom: 1px solid #eee;
	}

	.event-li:last-child { border-bottom: none; }

	.event-info { flex: 1; }
	.event-info p { margin: 0.25rem 0 0; color: #555; font-size: 0.9rem; }

	.item-actions {
		display: flex;
		gap: 0.4rem;
		margin-top: 0.4rem;
		justify-content: flex-end;
	}

	.btn-edit {
		background: #f0f4ff;
		border: 1px solid #c0c8e8;
		color: #1a1a2e;
		padding: 0.3rem 0.6rem;
		border-radius: 0.3rem;
		cursor: pointer;
		font-size: 0.85rem;
	}

	.btn-edit:hover { background: #dce4ff; }

	.inline-edit { width: 100%; }

	.inline-edit-actions {
		display: flex;
		gap: 0.4rem;
		margin-top: 0.25rem;
	}

	.daily-author-tag { font-size: 0.85rem; color: #f59e0b; font-style: italic; }

	/* ── Position toggle HA ──────────────────────────────────── */
	.pos-toggle { display: flex; gap: 0.3rem; flex-shrink: 0; }
	.pos-btn {
		padding: 0.4rem 0.8rem;
		border: 2px solid #ddd;
		background: white;
		border-radius: 0.4rem;
		cursor: pointer;
		font-size: 0.9rem;
		font-weight: 600;
	}
	.pos-btn.active { background: #1a1a2e; color: white; border-color: #1a1a2e; }

	/* ── Restore backup ──────────────────────────────────── */
	.btn-restore {
		display: block;
		width: 100%;
		padding: 0.9rem;
		background: #fff8e8;
		color: #7a4a00;
		border: 2px solid #e6a800;
		border-radius: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		text-align: center;
		box-sizing: border-box;
	}

	.btn-restore:hover:not(.restoring) { background: #fff0c0; }
	.btn-restore.restoring { opacity: 0.6; cursor: wait; }

	.toast {
		position: fixed;
		bottom: 2rem;
		left: 50%;
		transform: translateX(-50%);
		background: #1a1a2e;
		color: #ffd700;
		padding: 1rem 2rem;
		border-radius: 2rem;
		font-size: 1.1rem;
		font-weight: 600;
		z-index: 999;
	}
</style>
