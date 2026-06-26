<script lang="ts">
	import { onMount } from 'svelte';
	import { API } from '$lib/store';

	let household = $state({ display_name: '', reassurance_message: '' });
	let faqs = $state<Array<{ id: number; question: string; answer: string }>>([]);
	let events = $state<Array<{ id: number; title: string; event_date: string; event_time: string | null; recurrence: string | null; recurrence_end: string | null; message_before: string | null }>>([]);
	let people = $state<Array<{ id: number; first_name: string; relation: string; is_primary_caregiver: boolean }>>([]);

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
	let newPerson = $state({ first_name: '', relation: '', message: '', is_primary_caregiver: false });

	let toast = $state('');
	let activeTab = $state('message');

	async function load() {
		const [h, f, e, p] = await Promise.all([
			fetch(`${API}/api/household`).then(r => r.json()),
			fetch(`${API}/api/faqs`).then(r => r.json()),
			fetch(`${API}/api/events`).then(r => r.json()),
			fetch(`${API}/api/people`).then(r => r.json()),
		]);
		household = h || household;
		faqs = f;
		events = e;
		people = p;
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

	async function addPerson() {
		await fetch(`${API}/api/people`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(newPerson),
		});
		newPerson = { first_name: '', relation: '', message: '', is_primary_caregiver: false };
		await load();
		showToast('Proche ajouté ✓');
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
		{#each ['message', 'agenda', 'faq', 'proches', 'maison'] as tab}
			<button class:active={activeTab === tab} onclick={() => activeTab = tab}>
				{tab === 'message' ? '✉️ Message' :
				 tab === 'agenda' ? '📅 Agenda' :
				 tab === 'faq' ? '💬 Questions' :
				 tab === 'proches' ? '👨‍👩‍👧 Proches' : '🏠 Maison'}
			</button>
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
			<textarea bind:value={newPerson.message} rows="2" placeholder="Message rassurant..."></textarea>
			<label class="checkbox">
				<input type="checkbox" bind:checked={newPerson.is_primary_caregiver} />
				Aidant principal (photo affichée en premier)
			</label>
			<button class="primary" onclick={addPerson} disabled={!newPerson.first_name.trim()}>Ajouter</button>
		</section>

		<section class="card">
			<h2>Proches enregistrés</h2>
			{#if people.length === 0}
				<p class="empty">Aucun proche.</p>
			{:else}
				<ul class="list">
					{#each people as p}
						<li><strong>{p.first_name}</strong> — {p.relation} {p.is_primary_caregiver ? '⭐' : ''}</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}

	{#if activeTab === 'maison'}
		<section class="card">
			<h2>Informations de la maison</h2>
			<input type="text" bind:value={household.display_name} placeholder="Nom affiché (ex: chez Gaëtan)" />
			<textarea bind:value={household.reassurance_message} rows="3" placeholder="Message rassurant principal"></textarea>
			<button class="primary" onclick={saveHousehold}>Enregistrer</button>
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
