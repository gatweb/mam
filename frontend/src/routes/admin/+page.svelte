<script lang="ts">
	import { onMount } from 'svelte';
	import { API } from '$lib/store';

	let household = $state({ display_name: '', reassurance_message: '' });
	let faqs = $state<Array<{ id: number; question: string; answer: string }>>([]);
	let events = $state<Array<{ id: number; title: string; event_date: string; event_time: string | null; recurrence: string | null; recurrence_end: string | null; message_before: string | null }>>([]);
	let people = $state<Array<{ id: number; first_name: string; relation: string; message: string | null; next_visit: string | null; photo_path: string | null; is_primary_caregiver: boolean; allow_video_call: boolean }>>([]);

	let quickMsg = $state({ content: '', author: 'Gaëtan' });
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

	let newEvent = $state({ title: '', event_date: new Date().toISOString().slice(0, 10), event_time: '', message_before: '', message_during: '', message_after: '' });
	let newFaq = $state({ question: '', answer: '' });
	let newPerson = $state({ first_name: '', relation: '', message: '', is_primary_caregiver: false, allow_video_call: false });
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
	});
	let testingNotif = $state(false);
	let testingHa = $state(false);
	let haEntities = $state<Array<{ id: number; entity_id: string; label: string; icon: string; unit: string }>>([]);
	let newHaEntity = $state({ entity_id: '', label: '', icon: '🌡️', unit: '' });
	let haSearch = $state('');
	let haSearchResults = $state<Array<{ entity_id: string; friendly_name: string; state: string; unit: string }>>([]);
	let haSearching = $state(false);

	let toast = $state('');
	let activeTab = $state('message');

	async function load() {
		const [h, f, e, p, st, ha, ph] = await Promise.all([
			fetch(`${API}/api/household`).then(r => r.json()),
			fetch(`${API}/api/faqs`).then(r => r.json()),
			fetch(`${API}/api/events`).then(r => r.json()),
			fetch(`${API}/api/people`).then(r => r.json()),
			fetch(`${API}/api/settings`).then(r => r.json()),
			fetch(`${API}/api/ha/entities`).then(r => r.json()),
			fetch(`${API}/api/photos`).then(r => r.json()),
		]);
		household = h || household;
		faqs = f;
		events = e;
		people = p;
		if (st) settings = { ...settings, ...st };
		haEntities = ha;
		photos = ph;
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
			body: JSON.stringify({ ...newHaEntity, display_order: haEntities.length }),
		});
		newHaEntity = { entity_id: '', label: '', icon: '🌡️', unit: '' };
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
		showToast('Message envoyé à l\'écran ✓');
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
		newEvent = { title: '', event_date: new Date().toISOString().slice(0, 10), event_time: '', message_before: '', message_during: '', message_after: '' };
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
		newPerson = { first_name: '', relation: '', message: '', is_primary_caregiver: false };
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
			<h2>Message immédiat</h2>
			<p class="hint">Apparaît sur l'écran en quelques secondes.</p>
			<textarea bind:value={quickMsg.content} rows="4" placeholder="Je suis allé faire les courses. Je reviens vers 17h. Tout va bien."></textarea>
			<input type="text" bind:value={quickMsg.author} placeholder="Ton prénom (ex: Gaëtan)" />
			<button class="primary" onclick={sendQuickMessage} disabled={!quickMsg.content.trim()}>
				Envoyer maintenant
			</button>
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
						<li>
							<div>
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
									{#if e.recurrence_end}
										<span class="rec-end"> · jusqu'au {e.recurrence_end}</span>
									{/if}
								</div>
							</div>
							<button class="del" onclick={() => deleteEvent(e.id)}>✕</button>
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
						<li>
							<div>
								<strong>{f.question}</strong>
								<p>{f.answer}</p>
							</div>
							<button class="del" onclick={() => deleteFaq(f.id)}>✕</button>
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
			<label class="checkbox">
				<input type="checkbox" bind:checked={newPerson.is_primary_caregiver} />
				Aidant principal (affiché en premier sur l'écran)
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
			<h2>Proches enregistrés</h2>
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

							<!-- Info -->
							<div class="person-details">
								<strong>{person.first_name}</strong>
								{#if person.is_primary_caregiver}<span class="badge">⭐ principal</span>{/if}
								<div class="person-relation-text">{person.relation}</div>
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
								<button class="del" onclick={() => deletePerson(person.id)} title="Supprimer">✕</button>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'photos'}
		<section class="card">
			<h2>Ajouter des photos</h2>
			<p class="hint">Les photos défilent en diaporama sur l'écran de Martine. Vous pouvez en ajouter plusieurs à la fois.</p>
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
										placeholder="Légende (ex: Gaëtan et Martine, Noël 2023)"
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
			<h2>🏠 Home Assistant</h2>
			<p class="hint">Affichez la température, la présence ou n'importe quel capteur HA sur l'écran de Martine.</p>

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
				<button class="primary" onclick={addHaEntity} disabled={!newHaEntity.entity_id.trim()}>Ajouter à l'écran</button>
			</div>

			<!-- Liste des entités configurées -->
			{#if haEntities.length > 0}
				<ul class="list" style="margin-top:0.75rem">
					{#each haEntities as ent}
						<li>
							<div>
								<strong>{ent.icon} {ent.label}</strong>
								<div class="event-meta">{ent.entity_id}{ent.unit ? ` · ${ent.unit}` : ''}</div>
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

		<section class="card danger-zone">
			<h2>Données de démonstration</h2>
			<p class="hint">Recharge les exemples de départ (Martine, Gaëtan, Sophie, événements et questions types). Les données actuelles seront effacées.</p>
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
