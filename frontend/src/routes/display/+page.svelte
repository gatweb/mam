<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { displayState, API } from '$lib/store';
	import { getMoment, getMomentLabel, formatDate, formatTime, eventStatus } from '$lib/time';

	let now = $state(new Date());
	let moment = $derived(getMoment(now.getHours()));
	let faqIndex = $state(0);

	let clockInterval: ReturnType<typeof setInterval>;
	let faqInterval: ReturnType<typeof setInterval>;
	let ws: WebSocket;

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
		};
		ws.onclose = () => setTimeout(connectWs, 3000);
	}

	onMount(() => {
		fetchState();
		connectWs();

		clockInterval = setInterval(() => {
			now = new Date();
		}, 10000);

		faqInterval = setInterval(() => {
			if ($displayState?.faqs?.length) {
				faqIndex = (faqIndex + 1) % $displayState.faqs.length;
			}
		}, 12000);
	});

	onDestroy(() => {
		clearInterval(clockInterval);
		clearInterval(faqInterval);
		ws?.close();
	});

	const isNight = $derived(moment === 'nuit');
	const isSundown = $derived(moment === 'soir');
	const currentFaq = $derived($displayState?.faqs?.[faqIndex] ?? null);
	const primaryPerson = $derived($displayState?.people?.find(p => p.is_primary_caregiver) ?? $displayState?.people?.[0] ?? null);
</script>

<svelte:head>
	<title>Snoozolène</title>
</svelte:head>

<main class="screen" class:night={isNight} class:sundown={isSundown && !isNight}>

	<!-- HEURE & DATE -->
	<section class="time-block">
		<div class="clock">{formatTime(now)}</div>
		<div class="date">{formatDate(now).toUpperCase()}</div>
		<div class="moment">{getMomentLabel(moment)}</div>
	</section>

	<!-- MODE NUIT : affichage minimal -->
	{#if isNight}
		<section class="night-message">
			{#if $displayState?.household}
				<p>Tu es {$displayState.household.display_name}.</p>
			{/if}
			<p>Tout va bien.</p>
			<p>Tu peux te recoucher.</p>
		</section>

	{:else}
		<!-- LIEU & RÉASSURANCE -->
		<section class="location-block">
			{#if $displayState?.household}
				<p class="location">{$displayState.household.reassurance_message}</p>
			{/if}
		</section>

		<!-- MESSAGE DU JOUR (envoyé par l'aidant) -->
		{#if $displayState?.daily_message}
			<section class="daily-message">
				<p>{$displayState.daily_message.content}</p>
				{#if $displayState.daily_message.author}
					<span class="author">— {$displayState.daily_message.author}</span>
				{/if}
			</section>
		{/if}

		<!-- ÉVÉNEMENTS DU JOUR -->
		{#if $displayState?.events_today?.length}
			<section class="events-block">
				<h2>Aujourd'hui :</h2>
				<ul>
					{#each $displayState.events_today as event}
						{@const status = eventStatus(event.event_time, now)}
						<li class="event" class:active={status === 'during'}>
							{#if status === 'before' && event.message_before}
								{event.message_before}
							{:else if status === 'during' && event.message_during}
								{event.message_during}
							{:else if status === 'after' && event.message_after}
								{event.message_after}
							{:else}
								{event.title}{event.event_time ? ` à ${event.event_time.replace(':', ' h ')}` : ''}
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- FAQ défilante -->
		{#if currentFaq}
			<section class="faq-block">
				<p class="faq-answer">{currentFaq.answer}</p>
			</section>
		{/if}

		<!-- PHOTO + NOM du proche principal -->
		{#if primaryPerson}
			<section class="person-block">
				{#if primaryPerson.photo_path}
					<img src="{API}{primaryPerson.photo_path}" alt={primaryPerson.first_name} class="person-photo" />
				{/if}
				<div class="person-info">
					<span class="person-name">{primaryPerson.first_name}</span>
					<span class="person-relation">{primaryPerson.relation}</span>
					{#if primaryPerson.message}
						<span class="person-message">{primaryPerson.message}</span>
					{/if}
				</div>
			</section>
		{/if}
	{/if}

</main>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
		font-family: 'Segoe UI', system-ui, sans-serif;
		background: #1a1a2e;
		color: #f0f0f0;
	}

	.screen {
		display: grid;
		grid-template-rows: auto auto auto 1fr auto auto;
		gap: 1.5rem;
		height: 100vh;
		padding: 2.5rem 3rem;
		box-sizing: border-box;
		background: #1a1a2e;
		transition: background 1s ease;
	}

	.screen.sundown { background: #2d1b00; }

	.screen.night {
		background: #080810;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		gap: 2rem;
	}

	.clock {
		font-size: clamp(5rem, 14vw, 10rem);
		font-weight: 700;
		color: #ffd700;
		letter-spacing: 0.05em;
		text-align: center;
	}

	.date {
		font-size: clamp(1.8rem, 4vw, 3.5rem);
		font-weight: 600;
		color: #e0e0e0;
		margin-top: 0.2rem;
		text-align: center;
	}

	.moment {
		font-size: clamp(1.4rem, 3vw, 2.5rem);
		color: #a0c4ff;
		letter-spacing: 0.2em;
		margin-top: 0.3rem;
		text-align: center;
	}

	.location-block .location {
		font-size: clamp(1.6rem, 3.5vw, 3rem);
		font-weight: 500;
		color: #90ee90;
		text-align: center;
		margin: 0;
	}

	.daily-message {
		background: rgba(255, 215, 0, 0.12);
		border-left: 6px solid #ffd700;
		border-radius: 0.5rem;
		padding: 1rem 1.5rem;
		font-size: clamp(1.4rem, 3vw, 2.2rem);
	}

	.daily-message p { margin: 0; }
	.author { font-size: 0.8em; color: #ffd700; }

	.events-block h2 {
		font-size: clamp(1.3rem, 2.5vw, 2rem);
		color: #a0c4ff;
		margin: 0 0 0.5rem;
	}

	.events-block ul { list-style: none; padding: 0; margin: 0; }

	.events-block .event {
		font-size: clamp(1.3rem, 2.8vw, 2.2rem);
		padding: 0.3rem 0;
		color: #e0e0e0;
	}

	.events-block .event::before { content: '• '; color: #ffd700; }
	.events-block .event.active { color: #ffd700; font-weight: 600; }

	.faq-block {
		text-align: center;
		border-top: 1px solid rgba(255,255,255,0.1);
		padding-top: 1rem;
	}

	.faq-answer {
		font-size: clamp(1.3rem, 2.8vw, 2.2rem);
		color: #d0d0d0;
		font-style: italic;
		margin: 0;
	}

	.person-block {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.person-photo {
		width: clamp(80px, 12vw, 160px);
		height: clamp(80px, 12vw, 160px);
		border-radius: 50%;
		object-fit: cover;
		border: 4px solid #ffd700;
	}

	.person-info { display: flex; flex-direction: column; }

	.person-name {
		font-size: clamp(1.4rem, 3vw, 2.5rem);
		font-weight: 700;
		color: #ffd700;
	}

	.person-relation {
		font-size: clamp(1.1rem, 2.2vw, 1.8rem);
		color: #a0c4ff;
	}

	.person-message {
		font-size: clamp(1rem, 2vw, 1.6rem);
		color: #d0d0d0;
		font-style: italic;
		margin-top: 0.3rem;
	}

	.night-message { text-align: center; }

	.night-message p {
		font-size: clamp(2rem, 5vw, 4rem);
		margin: 0.5rem 0;
		color: #d0d0ff;
	}
</style>
