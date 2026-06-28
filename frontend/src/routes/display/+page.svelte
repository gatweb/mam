<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { displayState, API } from '$lib/store';
	import { getMoment, getMomentLabel, formatDate, formatTime, eventStatus, isNightTime } from '$lib/time';

	let now = $state(new Date());
	let moment = $derived(getMoment(
		now.getHours(),
		$displayState?.night_start ?? '21:30',
		$displayState?.night_end ?? '07:00'
	));
	let faqIndex = $state(0);
	let photoIndex = $state(0);
	let photoVisible = $state(true);
	let videoCall = $state<{ room: string; personName: string | null } | null>(null);
	let alarmActive = $state(false);
	let alarmTime = $state('');
	let alarmAudio: HTMLAudioElement | null = null;

	let clockInterval: ReturnType<typeof setInterval>;
	let faqInterval: ReturnType<typeof setInterval>;
	let photoInterval: ReturnType<typeof setInterval>;
	let ws: WebSocket;
	let wakeLock: WakeLockSentinel | null = null;

	async function requestWakeLock() {
		try {
			wakeLock = await (navigator as any).wakeLock?.request('screen');
		} catch (e) {
			// pas supporté ou refusé, on continue sans
		}
	}

	async function fetchState() {
		try {
			const res = await fetch(`${API}/api/display`);
			const data = await res.json();
			displayState.set(data);
		} catch (e) {
			// keep last known state
		}
	}

	function connectWs() {
		const wsUrl = API.replace('http', 'ws') + '/ws';
		ws = new WebSocket(wsUrl);
		ws.onmessage = (e) => {
			const msg = JSON.parse(e.data);
			if (msg.type === 'refresh') fetchState();
			if (msg.type === 'video_call') videoCall = { room: msg.room, personName: msg.person_name ?? null };
			if (msg.type === 'video_call_end') videoCall = null;
			if (msg.type === 'alarm') {
				alarmActive = true;
				alarmTime = msg.time ?? '';
				if (msg.music_url) {
					alarmAudio = new Audio(msg.music_url);
					alarmAudio.loop = true;
					alarmAudio.play().catch(() => {});
				}
			}
			if (msg.type === 'alarm_stop') {
				alarmActive = false;
				alarmAudio?.pause();
				alarmAudio = null;
			}
		};
		ws.onclose = () => setTimeout(connectWs, 3000);
	}

	onMount(() => {
		fetchState();
		connectWs();
		requestWakeLock();
		// Re-acquérir le wake lock si la page redevient visible (ex: retour de veille)
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState === 'visible') requestWakeLock();
		});
		clockInterval = setInterval(() => { now = new Date(); }, 10000);
		faqInterval = setInterval(() => {
			if ($displayState?.faqs?.length) {
				faqIndex = (faqIndex + 1) % $displayState.faqs.length;
			}
		}, 12000);
		photoInterval = setInterval(() => {
			const photos = $displayState?.photos ?? [];
			if (photos.length > 1) {
				photoVisible = false;
				setTimeout(() => {
					photoIndex = (photoIndex + 1) % photos.length;
					photoVisible = true;
				}, 700);
			}
		}, 18000);
	});

	onDestroy(() => {
		clearInterval(clockInterval);
		clearInterval(faqInterval);
		clearInterval(photoInterval);
		ws?.close();
		wakeLock?.release();
	});

	function _formatHaState(state: string, entityId: string): string {
		if (entityId.startsWith('device_tracker.')) return state === 'home' ? 'À la maison' : 'Absent';
		if (state === 'on') return 'Ouvert';
		if (state === 'off') return 'Fermé';
		const n = parseFloat(state);
		if (!isNaN(n)) return n % 1 === 0 ? String(n) : n.toFixed(1);
		return state;
	}

	const isNight = $derived(moment === 'nuit');
	const currentFaq = $derived($displayState?.faqs?.[faqIndex] ?? null);
	const currentPhoto = $derived($displayState?.photos?.[photoIndex] ?? null);
	const primaryPerson = $derived($displayState?.people?.find((p: any) => p.is_primary_caregiver) ?? $displayState?.people?.[0] ?? null);
	const presentPeople = $derived(($displayState?.people ?? []).filter((p: any) => p.is_primary_caregiver));
	const upcomingBirthdays = $derived(($displayState?.birthdays ?? []) as Array<{ first_name: string; relation: string; photo_path: string | null; days_until: number; age: number }>);
	const haPosition = $derived(($displayState as any)?.ha_position ?? 'bottom');

	const presentSentence = $derived(
		presentPeople.length === 0 ? '' :
		presentPeople.length === 1 ? `${presentPeople[0].first_name} est avec toi aujourd'hui.` :
		presentPeople.slice(0, -1).map((p: any) => p.first_name).join(', ')
			+ ` et ${presentPeople[presentPeople.length - 1].first_name} sont avec toi aujourd'hui.`
	);

	function getSeason(d: Date): 'printemps' | 'ete' | 'automne' | 'hiver' {
		const m = d.getMonth() + 1;
		const day = d.getDate();
		if ((m === 3 && day >= 20) || m === 4 || m === 5 || (m === 6 && day < 21)) return 'printemps';
		if ((m === 6 && day >= 21) || m === 7 || m === 8 || (m === 9 && day < 22)) return 'ete';
		if ((m === 9 && day >= 22) || m === 10 || m === 11 || (m === 12 && day < 21)) return 'automne';
		return 'hiver';
	}

	const season = $derived(getSeason(now));
	const todayWeather = $derived($displayState?.weather?.[0] ?? null);
</script>

<svelte:head>
	<title>Snoozolène</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&family=Playfair+Display:wght@700&display=swap" rel="stylesheet" />
</svelte:head>

<main class="screen {moment} {season}" class:night={isNight}>

	<!-- Icône météo en filigrane -->
	{#if todayWeather && !isNight}
		<div class="weather-watermark">{todayWeather.icon}</div>
	{/if}

	{#if isNight}
		<!-- ══════════════ MODE NUIT ══════════════ -->
		<div class="night-screen">
			<div class="night-clock">{formatTime(now)}</div>
			<div class="night-date">{formatDate(now).toUpperCase()}</div>
			{#if $displayState?.household}
				<p class="night-msg">{$displayState.household.reassurance_message}</p>
			{/if}
		</div>

	{:else}
		<!-- ══════════════ MODE JOUR ══════════════ -->

		<!-- ZONE TOP : anniversaires + météo (une seule ligne de grille) -->
		<header class="top-zone">
			<!-- Bannière anniversaire (dans la zone météo) -->
			{#each upcomingBirthdays as bday}
				<div class="birthday-banner">
					{#if bday.photo_path}
						<img src="{API}{bday.photo_path}" alt={bday.first_name} class="bday-avatar" />
					{:else}
						<span class="bday-cake">🎂</span>
					{/if}
					<div class="bday-text">
						{#if bday.days_until === 0}
							<span class="bday-main">🎉 Aujourd'hui c'est l'anniversaire de {bday.first_name} !</span>
							<span class="bday-sub">Bon anniversaire {bday.relation} · {bday.age} ans 🎈</span>
						{:else if bday.days_until === 1}
							<span class="bday-main">🎂 Demain c'est l'anniversaire de {bday.first_name}</span>
							<span class="bday-sub">{bday.relation} · {bday.age} ans</span>
						{:else}
							<span class="bday-main">🎂 Dans {bday.days_until} jours : anniversaire de {bday.first_name}</span>
							<span class="bday-sub">{bday.relation} · {bday.age} ans</span>
						{/if}
					</div>
				</div>
			{/each}

			<!-- Bandeau météo -->
			<div class="weather-strip">
				{#if $displayState?.weather?.length}
					{#each $displayState.weather as day, i}
						<div class="wday" class:wday-today={i === 0}>
							<span class="wday-name">{day.day}</span>
							<span class="wday-icon">{day.icon}</span>
							<span class="wday-max">{day.tmax}°</span>
							<span class="wday-min">{day.tmin}°</span>
						</div>
					{/each}
				{/if}
				<div class="moment-pill">{getMomentLabel(moment)}</div>
				<!-- Capteurs HA en haut -->
				{#if haPosition === 'top' && $displayState?.ha_states?.length}
					<div class="ha-chips-top">
						{#each $displayState.ha_states as sensor}
							<div class="ha-chip-top glass">
								<span>{sensor.icon}</span>
								<span class="ha-chip-top-val">{_formatHaState(sensor.state, sensor.entity_id)}{sensor.unit}</span>
								<span class="ha-chip-top-label">{sensor.label}</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</header>

		<!-- GRILLE PRINCIPALE -->
		<div class="main-grid">

			<!-- ── COLONNE GAUCHE ── -->
			<section class="left-col">

				<!-- Horloge + date -->
				<div class="clock-block glass">
					<div class="clock">{formatTime(now)}</div>
					<div class="date-line">{formatDate(now).toUpperCase()}</div>
					{#if $displayState?.household}
						<div class="reassurance">{$displayState.household.reassurance_message}</div>
					{/if}
					{#if presentSentence}
						<div class="present-sentence">👋 {presentSentence}</div>
					{/if}
				</div>

				<!-- Message du jour -->
				{#if $displayState?.daily_message}
					<div class="daily-card glass">
						<span class="daily-icon">✉️</span>
						<div class="daily-body">
							<p class="daily-text">{$displayState.daily_message.content}</p>
							{#if $displayState.daily_message.author}
								<span class="daily-author">— {$displayState.daily_message.author}</span>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Événements du jour -->
				{#if $displayState?.events_today?.length}
					<div class="events-card glass">
						<p class="events-title">Aujourd'hui</p>
						<ul class="events-list">
							{#each $displayState.events_today.slice(0, 3) as event}
								{@const status = eventStatus(event.event_time, now)}
								<li class="event-item" class:event-active={status === 'during'}>
									<span class="event-dot"></span>
									<span class="event-text">
										{#if status === 'before' && event.message_before}
											{event.message_before}
										{:else if status === 'during' && event.message_during}
											{event.message_during}
										{:else if status === 'after' && event.message_after}
											{event.message_after}
										{:else}
											{event.title}{event.event_time ? ` · ${event.event_time.replace(':', 'h')}` : ''}
										{/if}
									</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Carte Q/R -->
				{#if currentFaq}
					<div class="faq-card glass">
						<p class="faq-label">💬 Question</p>
						<p class="faq-question">{currentFaq.question}</p>
						<p class="faq-answer">{currentFaq.answer}</p>
					</div>
				{/if}

			</section>

			<!-- ── COLONNE DROITE : photo ── -->
			<section class="right-col">
				{#if currentPhoto}
					<div class="slideshow" class:visible={photoVisible}>
						<img src="{API}{currentPhoto.path}" alt={currentPhoto.caption ?? ''} class="slide-img" />
						{#if currentPhoto.caption}
							<p class="slide-caption">{currentPhoto.caption}</p>
						{/if}
					</div>
				{:else if primaryPerson?.photo_path}
					<div class="slideshow visible">
						<img src="{API}{primaryPerson.photo_path}" alt={primaryPerson.first_name} class="slide-img" />
						<p class="slide-caption">{primaryPerson.first_name} · {primaryPerson.relation}</p>
					</div>
				{/if}
			</section>

		</div>

		<!-- BARRE DU BAS -->
		<footer class="bottom-bar">

			<!-- Proches présents -->
			{#if presentPeople.length > 0}
				{#each presentPeople as person}
					<div class="person-chip glass">
						{#if person.photo_path}
							<img src="{API}{person.photo_path}" alt={person.first_name} class="person-avatar" />
						{:else}
							<div class="person-avatar person-initial">{person.first_name[0]}</div>
						{/if}
						<div class="person-info">
							<span class="person-name">{person.first_name}</span>
							<span class="person-rel">{person.relation}</span>
						</div>
					</div>
				{/each}
			{:else if primaryPerson}
				<div class="person-chip glass">
					{#if primaryPerson.photo_path}
						<img src="{API}{primaryPerson.photo_path}" alt={primaryPerson.first_name} class="person-avatar" />
					{:else}
						<div class="person-avatar person-initial">{primaryPerson.first_name[0]}</div>
					{/if}
					<div class="person-info">
						<span class="person-name">{primaryPerson.first_name}</span>
						<span class="person-rel">{primaryPerson.relation}</span>
					</div>
				</div>
			{/if}

			<!-- Capteurs HA en bas -->
			{#if haPosition === 'bottom' && $displayState?.ha_states?.length}
				<div class="ha-chips">
					{#each $displayState.ha_states as sensor}
						<div class="ha-chip glass">
							<span class="ha-chip-icon">{sensor.icon}</span>
							<span class="ha-chip-val">{_formatHaState(sensor.state, sensor.entity_id)}{sensor.unit}</span>
							<span class="ha-chip-label">{sensor.label}</span>
						</div>
					{/each}
				</div>
			{/if}


		</footer>

	{/if}
</main>

<!-- Overlay réveil -->
{#if alarmActive}
	<div
		class="alarm-overlay"
		role="button"
		tabindex="0"
		aria-label="Appuyer pour arrêter le réveil"
		onclick={async () => { alarmActive = false; alarmAudio?.pause(); alarmAudio = null; await fetch(`${API}/api/alarm/stop`, { method: 'POST' }); }}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { alarmActive = false; alarmAudio?.pause(); alarmAudio = null; fetch(`${API}/api/alarm/stop`, { method: 'POST' }); } }}
	>
		<div class="alarm-sun">☀️</div>
		<div class="alarm-time">{alarmTime}</div>
		<p class="alarm-msg">Bonjour ! C'est l'heure de se lever.</p>
		<p class="alarm-sub">Prenez votre temps, tout va bien.</p>
		<p class="alarm-dismiss">Appuyer pour continuer →</p>
	</div>
{/if}

<!-- Overlay appel vidéo -->
{#if videoCall}
	<div class="video-overlay">
		<div class="video-header">
			<span class="video-caller">📞 {videoCall.personName ? `Appel de ${videoCall.personName}` : 'Appel vidéo'}</span>
		</div>
		<iframe
			src="https://meet.jit.si/{videoCall.room}#config.prejoinPageEnabled=false&config.startWithVideoMuted=false&config.startWithAudioMuted=false&userInfo.displayName=Agnès"
			allow="camera; microphone; display-capture; autoplay"
			title="Appel vidéo"
		></iframe>
	</div>
{/if}

<style>
	@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&family=Playfair+Display:wght@700&display=swap');

	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
		font-family: 'Nunito', system-ui, sans-serif;
		background: #0f172a;
		color: #f0f4ff;
	}

	/* ── Fonds dynamiques par moment ─────────────────────── */
	.screen {
		height: 100vh;
		display: grid;
		grid-template-rows: auto 1fr auto;
		position: relative;
		overflow: hidden;
		transition: background 2s ease;
	}

	/* Défauts jour (hiver) */
	.screen.matin      { background: linear-gradient(145deg, #0f172a 0%, #1e3a5f 45%, #2d5986 100%); }
	.screen.apres-midi { background: linear-gradient(145deg, #0c1e3a 0%, #163566 45%, #1e4d8c 100%); }
	.screen.soir       { background: linear-gradient(145deg, #1a0a2e 0%, #3d1a4a 35%, #7a2e2e 65%, #b84a1a 100%); }
	.screen.night,
	.screen.nuit       { background: linear-gradient(145deg, #03040f 0%, #060818 100%); }

	/* Printemps — vert tendre, lilas */
	.screen.printemps.matin      { background: linear-gradient(145deg, #0d1f1a 0%, #1a3d2e 40%, #2d5a3e 100%); }
	.screen.printemps.apres-midi { background: linear-gradient(145deg, #0f1f18 0%, #1e4030 45%, #2e6645 100%); }
	.screen.printemps.soir       { background: linear-gradient(145deg, #1a0d2e 0%, #3d1a4a 35%, #5a2e5a 65%, #7a3a7a 100%); }

	/* Été — chaud, azur */
	.screen.ete.matin      { background: linear-gradient(145deg, #0a1a2e 0%, #0d3060 40%, #1a5080 100%); }
	.screen.ete.apres-midi { background: linear-gradient(145deg, #0a1528 0%, #0d2a50 40%, #1a4a78 100%); }
	.screen.ete.soir       { background: linear-gradient(145deg, #1a0a20 0%, #3a1040 35%, #6a2a15 65%, #a04010 100%); }

	/* Automne — ocre, brun, rouille */
	.screen.automne.matin      { background: linear-gradient(145deg, #1a100a 0%, #3a2010 40%, #6a4015 100%); }
	.screen.automne.apres-midi { background: linear-gradient(145deg, #180e08 0%, #362010 40%, #5a380f 100%); }
	.screen.automne.soir       { background: linear-gradient(145deg, #1a0808 0%, #401010 35%, #7a2810 65%, #a03a05 100%); }

	/* Bannière anniversaire */
	.birthday-banner {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.6rem 1.5rem;
		background: linear-gradient(90deg, rgba(255,215,0,0.18) 0%, rgba(255,150,0,0.12) 100%);
		border-bottom: 1px solid rgba(255,215,0,0.25);
		z-index: 2;
		animation: bday-slide-in 0.8s ease;
	}

	@keyframes bday-slide-in {
		from { opacity: 0; transform: translateY(-10px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	.bday-avatar {
		width: clamp(36px, 5vw, 52px);
		height: clamp(36px, 5vw, 52px);
		border-radius: 50%;
		object-fit: cover;
		border: 2px solid #ffd700;
		flex-shrink: 0;
	}

	.bday-cake { font-size: clamp(2rem, 4vw, 3rem); flex-shrink: 0; }

	.bday-text { display: flex; flex-direction: column; gap: 0.1rem; }

	.bday-main {
		font-size: clamp(1.1rem, 2vw, 1.6rem);
		font-weight: 700;
		color: #ffd700;
	}

	.bday-sub {
		font-size: clamp(0.9rem, 1.5vw, 1.2rem);
		color: rgba(255,215,0,0.65);
	}

	/* ── Filigrane météo ──────────────────────────────────── */
	.weather-watermark {
		position: absolute;
		right: -2rem;
		top: 50%;
		transform: translateY(-50%);
		font-size: clamp(12rem, 30vw, 22rem);
		opacity: 0.04;
		pointer-events: none;
		user-select: none;
		z-index: 0;
		filter: blur(2px);
	}

	/* ── Glassmorphism ────────────────────────────────────── */
	.glass {
		background: rgba(255, 255, 255, 0.07);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 1.2rem;
	}

	/* ── ZONE TOP (anniversaires + météo = 1 seule ligne de grille) ── */
	.top-zone {
		display: flex;
		flex-direction: column;
		z-index: 1;
		position: relative;
	}

	/* ── MÉTÉO STRIP ──────────────────────────────────────── */
	.weather-strip {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.3rem 1.2rem;
		background: rgba(0, 0, 0, 0.2);
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	.wday {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.15rem 0.4rem;
		border-radius: 0.5rem;
		gap: 0.02rem;
		flex: 1;
		max-width: 60px;
	}

	.wday-today {
		background: rgba(255, 215, 0, 0.15);
		border: 1px solid rgba(255, 215, 0, 0.3);
	}

	.wday-name {
		font-size: clamp(0.65rem, 1vw, 0.85rem);
		color: #94a3b8;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.wday-icon { font-size: clamp(1rem, 1.8vw, 1.4rem); }
	.wday-max { font-size: clamp(0.85rem, 1.4vw, 1.1rem); font-weight: 800; color: #ffd700; }
	.wday-min { font-size: clamp(0.7rem, 1vw, 0.9rem); color: #64748b; }

	.moment-pill {
		margin-left: auto;
		background: rgba(160, 196, 255, 0.15);
		border: 1px solid rgba(160, 196, 255, 0.25);
		color: #a0c4ff;
		font-size: clamp(0.9rem, 1.6vw, 1.2rem);
		font-weight: 800;
		letter-spacing: 0.15em;
		padding: 0.35rem 1rem;
		border-radius: 2rem;
		white-space: nowrap;
	}

	/* ── GRILLE PRINCIPALE ────────────────────────────────── */
	.main-grid {
		display: grid;
		grid-template-columns: 1fr 38%;
		gap: 1rem;
		padding: 1rem 1.5rem;
		min-height: 0;
		z-index: 1;
		position: relative;
	}

	/* ── COLONNE GAUCHE ───────────────────────────────────── */
	.left-col {
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
		min-height: 0;
		overflow: hidden;
	}

	.clock-block {
		padding: 1rem 1.5rem;
		flex-shrink: 0;
	}

	.clock {
		font-family: 'Playfair Display', serif;
		font-size: clamp(5rem, 13vw, 10rem);
		font-weight: 700;
		color: #ffd700;
		line-height: 1;
		letter-spacing: -0.02em;
	}

	.date-line {
		font-size: clamp(1.2rem, 2.6vw, 2.2rem);
		font-weight: 600;
		color: #cbd5e1;
		letter-spacing: 0.08em;
		margin-top: 0.2rem;
	}

	.reassurance {
		font-size: clamp(1.1rem, 2vw, 1.6rem);
		color: #86efac;
		font-weight: 600;
		margin-top: 0.5rem;
	}

	.present-sentence {
		font-size: clamp(1rem, 1.8vw, 1.4rem);
		color: #fbbf24;
		font-weight: 600;
		margin-top: 0.3rem;
	}

	/* Message du jour */
	.daily-card {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-left: 3px solid #ffd700;
		flex-shrink: 0;
	}

	.daily-icon { font-size: 1.6rem; flex-shrink: 0; margin-top: 0.1rem; }
	.daily-body { flex: 1; min-width: 0; }
	.daily-text {
		margin: 0;
		font-size: clamp(1.1rem, 2.2vw, 1.7rem);
		font-weight: 600;
		color: #f8f8f8;
		line-height: 1.4;
	}
	.daily-author { font-size: 0.85em; color: #ffd700; }

	/* Événements */
	.events-card {
		padding: 0.7rem 1rem;
		flex-shrink: 0;
	}

	.events-title {
		font-size: clamp(0.9rem, 1.5vw, 1.2rem);
		font-weight: 800;
		color: #a0c4ff;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		margin: 0 0 0.4rem;
	}

	.events-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem; }

	.event-item {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		font-size: clamp(1.1rem, 2vw, 1.6rem);
		color: #e2e8f0;
	}

	.event-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #475569;
		flex-shrink: 0;
		margin-top: 0.4em;
	}

	.event-active { color: #ffd700; font-weight: 700; }
	.event-active .event-dot { background: #ffd700; box-shadow: 0 0 6px #ffd700; }

	/* ── COLONNE DROITE : diaporama ───────────────────────── */
	.right-col {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 0;
		position: relative;
	}

	.slideshow {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		height: 100%;
		opacity: 0;
		transition: opacity 0.7s ease;
	}

	.slideshow.visible { opacity: 1; }

	.slide-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: 1.5rem;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
		border: 2px solid rgba(255, 215, 0, 0.2);
	}

	.slide-caption {
		position: absolute;
		bottom: 0.5rem;
		left: 0; right: 0;
		text-align: center;
		font-size: clamp(1rem, 1.8vw, 1.4rem);
		color: rgba(255,255,255,0.85);
		font-style: italic;
		background: rgba(0,0,0,0.45);
		backdrop-filter: blur(8px);
		padding: 0.3rem 0.8rem;
		border-radius: 0 0 1.5rem 1.5rem;
		margin: 0;
	}

	/* ── BARRE DU BAS ─────────────────────────────────────── */
	.bottom-bar {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 1.5rem 0.75rem;
		z-index: 1;
		position: relative;
		min-height: 0;
	}

	.person-chip {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.4rem 0.9rem 0.4rem 0.4rem;
		flex-shrink: 0;
	}

	.person-avatar {
		width: clamp(36px, 5vw, 52px);
		height: clamp(36px, 5vw, 52px);
		border-radius: 50%;
		object-fit: cover;
		border: 2px solid rgba(255, 215, 0, 0.4);
	}

	.person-initial {
		background: #1e3a5f;
		color: #ffd700;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 800;
		font-size: 1.1rem;
	}

	.person-info { display: flex; flex-direction: column; line-height: 1.2; }
	.person-name { font-size: clamp(1rem, 1.8vw, 1.4rem); font-weight: 700; color: #ffd700; }
	.person-rel { font-size: clamp(0.85rem, 1.4vw, 1.1rem); color: #94a3b8; }

	/* Capteurs HA en haut (dans la barre météo) */
	.ha-chips-top {
		display: flex;
		gap: 0.4rem;
		margin-left: 0.5rem;
		border-left: 1px solid rgba(255,255,255,0.1);
		padding-left: 0.5rem;
	}

	.ha-chip-top {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.15rem 0.5rem;
		font-size: clamp(0.75rem, 1.2vw, 1rem);
	}

	.ha-chip-top-val { font-weight: 700; color: #ffd700; }
	.ha-chip-top-label { color: #64748b; font-size: 0.85em; }

	.ha-chips { display: flex; gap: 0.4rem; }

	.ha-chip {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.3rem 0.8rem;
	}

	.ha-chip-icon { font-size: clamp(1.1rem, 1.8vw, 1.5rem); }
	.ha-chip-val { font-size: clamp(1rem, 1.6vw, 1.3rem); font-weight: 700; color: #ffd700; }
	.ha-chip-label { font-size: clamp(0.75rem, 1.1vw, 1rem); color: #64748b; }

	/* ── Carte Q/R ───────────────────────────────────────── */
	.faq-card {
		padding: 1rem 1.2rem;
		border-left: 4px solid #a78bfa;
		flex-shrink: 0;
		animation: faq-in 0.6s ease;
	}

	@keyframes faq-in {
		from { opacity: 0; transform: translateY(8px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	.faq-label {
		font-size: clamp(0.8rem, 1.3vw, 1rem);
		font-weight: 800;
		color: #a78bfa;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		margin: 0 0 0.3rem;
	}

	.faq-question {
		font-size: clamp(1.2rem, 2.2vw, 1.8rem);
		font-weight: 700;
		color: #e2e8f0;
		margin: 0 0 0.5rem;
		line-height: 1.3;
	}

	.faq-answer {
		font-size: clamp(1.1rem, 2vw, 1.6rem);
		font-weight: 600;
		color: #86efac;
		margin: 0;
		line-height: 1.4;
	}

	/* ── MODE NUIT ────────────────────────────────────────── */
	.night-screen {
		height: 100vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		text-align: center;
		padding: 2rem;
		box-sizing: border-box;
	}

	.night-clock {
		font-family: 'Playfair Display', serif;
		font-size: clamp(6rem, 20vw, 14rem);
		font-weight: 700;
		color: rgba(160, 196, 255, 0.7);
		line-height: 1;
		letter-spacing: -0.02em;
	}

	.night-date {
		font-size: clamp(1.2rem, 3vw, 2.2rem);
		color: rgba(148, 163, 184, 0.5);
		letter-spacing: 0.1em;
		font-weight: 600;
	}

	.night-msg {
		font-size: clamp(1.2rem, 2.5vw, 2rem);
		color: rgba(134, 239, 172, 0.5);
		font-weight: 600;
		margin: 0.5rem 0 0;
		max-width: 600px;
	}

	/* ── RÉVEIL ──────────────────────────────────────────── */
	.alarm-overlay {
		position: fixed;
		inset: 0;
		z-index: 90;
		background: linear-gradient(145deg, #1a1a0a 0%, #3d3200 40%, #7a6500 100%);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		text-align: center;
		animation: alarm-fade-in 2s ease;
	}

	@keyframes alarm-fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	.alarm-sun {
		font-size: clamp(6rem, 18vw, 12rem);
		animation: alarm-pulse 3s ease-in-out infinite;
	}

	@keyframes alarm-pulse {
		0%, 100% { transform: scale(1); opacity: 0.9; }
		50% { transform: scale(1.08); opacity: 1; }
	}

	.alarm-time {
		font-family: 'Playfair Display', serif;
		font-size: clamp(5rem, 15vw, 11rem);
		font-weight: 700;
		color: #ffd700;
		line-height: 1;
	}

	.alarm-msg {
		font-size: clamp(2rem, 5vw, 4rem);
		font-weight: 700;
		color: #fef9c3;
		margin: 0;
	}

	.alarm-sub {
		font-size: clamp(1.3rem, 3vw, 2.5rem);
		color: rgba(254, 249, 195, 0.65);
		font-style: italic;
		margin: 0;
	}

	.alarm-dismiss {
		font-size: clamp(1rem, 2vw, 1.6rem);
		color: rgba(254, 249, 195, 0.4);
		margin: 1rem 0 0;
		letter-spacing: 0.05em;
	}

	.alarm-overlay { cursor: pointer; }

	/* ── APPEL VIDÉO ──────────────────────────────────────── */
	.video-overlay {
		position: fixed;
		inset: 0;
		z-index: 100;
		background: #000;
		display: flex;
		flex-direction: column;
	}

	.video-header {
		padding: 0.75rem 1.5rem;
		background: #0f172a;
		border-bottom: 1px solid rgba(255,215,0,0.2);
	}

	.video-caller { font-size: 1.3rem; font-weight: 700; color: #ffd700; }

	.video-overlay iframe { flex: 1; border: none; width: 100%; }
</style>
