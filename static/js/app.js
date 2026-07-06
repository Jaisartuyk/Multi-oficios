const root = document.documentElement;
const savedTheme = localStorage.getItem('obraya-theme');

if (savedTheme) {
    root.dataset.theme = savedTheme;
}

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function updateThemeIcon() {
    const toggle = document.querySelector('[data-theme-toggle] i');
    if (!toggle) return;
    toggle.setAttribute('data-lucide', root.dataset.theme === 'dark' ? 'sun' : 'moon');
    refreshIcons();
}

function getMapProfessionals(mapElement) {
    try {
        return JSON.parse(mapElement.dataset.professionals || '[]');
    } catch {
        return [];
    }
}

function setMapStatus(message) {
    const status = document.querySelector('[data-map-status-text]');
    if (status) {
        status.textContent = message;
    }
}

function showMapFallback(message) {
    const mapElement = document.getElementById('obraya-map');
    if (!mapElement) return;
    mapElement.classList.add('map-fallback');
    mapElement.classList.remove('map-ready');
    setMapStatus(message || 'Mapa visual de respaldo - revisa la API key de Google Maps');
    refreshIcons();
}

window.showObraYaMapFallback = showMapFallback;

window.renderObraYaMap = function renderObraYaMap() {
    const mapElement = document.getElementById('obraya-map');
    if (!mapElement) return;
    if (!window.google?.maps) {
        showMapFallback('Google Maps no cargo - revisa la API key o las restricciones');
        return;
    }
    if (mapElement.dataset.mapReady === 'true') return;

    const professionals = getMapProfessionals(mapElement);
    const center = { lat: -2.1894, lng: -79.8891 };
    const map = new google.maps.Map(mapElement, {
        center,
        zoom: 13,
        disableDefaultUI: true,
        zoomControl: true,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        styles: [
            { featureType: 'poi', stylers: [{ visibility: 'off' }] },
            { featureType: 'transit', stylers: [{ visibility: 'off' }] },
            { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#d9f4ef' }] },
            { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
            { featureType: 'landscape', elementType: 'geometry', stylers: [{ color: '#eef7f4' }] },
        ],
    });

    mapElement.classList.add('map-ready');
    mapElement.classList.remove('map-fallback');
    setMapStatus('Mapa activo: profesionales cercanos en Guayaquil');

    const infoWindow = new google.maps.InfoWindow();

    professionals.forEach((professional) => {
        const marker = new google.maps.Marker({
            position: { lat: professional.lat, lng: professional.lng },
            map,
            title: professional.name,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10,
                fillColor: '#18a76a',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 3,
            },
        });

        marker.addListener('click', () => {
            infoWindow.setContent(`
                <div class="map-info">
                    <strong>${professional.name}</strong>
                    <span>${professional.specialty}</span>
                    <small>${professional.level} - ${professional.rating} estrellas - ${professional.eta}</small>
                </div>
            `);
            infoWindow.open(map, marker);
        });
    });

    mapElement.dataset.mapReady = 'true';
};
function initProfessionalDashboard() {
    const sections = {
        '#professional-profile': document.getElementById('professional-profile'),
        '#job-market': document.getElementById('job-market'),
        '#my-jobs': document.getElementById('my-jobs')
    };

    if (!sections['#professional-profile'] && !sections['#job-market'] && !sections['#my-jobs']) {
        return;
    }

    const hero = document.querySelector('.profile-hero');
    const stats = document.querySelector('.reputation-grid');
    const navLinks = document.querySelectorAll('.bottom-nav a');

    function switchTab() {
        const hash = window.location.hash || '#professional-profile';
        const validHashes = Object.keys(sections);
        const activeHash = validHashes.includes(hash) ? hash : '#professional-profile';

        for (const [key, section] of Object.entries(sections)) {
            if (section) {
                if (key === activeHash) {
                    section.style.display = 'block';
                    section.style.opacity = '0';
                    section.style.transition = 'opacity 0.25s ease-in-out';
                    section.offsetHeight; // trigger reflow
                    section.style.opacity = '1';
                } else {
                    section.style.display = 'none';
                }
            }
        }

        if (hero) hero.style.display = (activeHash === '#professional-profile') ? 'block' : 'none';
        if (stats) stats.style.display = (activeHash === '#professional-profile') ? 'grid' : 'none';

        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (linkHref && linkHref.includes(activeHash)) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    switchTab();
    window.addEventListener('hashchange', switchTab);
}

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.querySelector('[data-theme-toggle]');

    toggle?.addEventListener('click', () => {
        root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('obraya-theme', root.dataset.theme);
        updateThemeIcon();
    });

    document.querySelectorAll('.category-card, .pro-card, .service-card').forEach((card, index) => {
        card.style.animation = `rise 420ms ease ${index * 35}ms both`;
    });

    document.querySelectorAll('[data-scroll-target]').forEach((button) => {
        button.addEventListener('click', () => {
            const target = document.getElementById(button.dataset.scrollTarget);
            target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            target?.classList.add('map-highlight');
            window.setTimeout(() => target?.classList.remove('map-highlight'), 1600);
        });
    });

    const mapElement = document.getElementById('obraya-map');
    if (mapElement?.dataset.hasKey === 'false') {
        showMapFallback('Mapa visual de respaldo - agrega GOOGLE_MAPS_API_KEY en .env');
    }

    if (window.__obraYaGoogleMapsReady) {
        window.renderObraYaMap();
    }

    window.setTimeout(() => {
        const currentMap = document.getElementById('obraya-map');
        if (currentMap?.dataset.hasKey === 'true' && currentMap.dataset.mapReady !== 'true') {
            showMapFallback('Google Maps no cargo - revisa API key, facturacion o restricciones');
        }
    }, 3500);

    initProfessionalDashboard();
    updateThemeIcon();
    refreshIcons();

    // PWA Installation prompt logic
    let deferredPrompt;
    const installBanner = document.getElementById('pwa-install-banner');
    const installBtn = document.getElementById('pwa-install-btn');
    const closeBtn = document.getElementById('pwa-close-btn');

    // Check if running in standalone mode (already installed)
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

    if (!isStandalone && localStorage.getItem('pwa-banner-dismissed') !== 'true') {
        window.addEventListener('beforeinstallprompt', (e) => {
            // Prevent Chrome 67 and earlier from automatically showing the prompt
            e.preventDefault();
            // Stash the event so it can be triggered later
            deferredPrompt = e;
            // Show the banner
            if (installBanner) {
                installBanner.style.display = 'flex';
                // Refresh Lucide icons in case they need to render inside the banner
                if (window.lucide) window.lucide.createIcons();
            }
        });
    }

    if (installBtn) {
        installBtn.addEventListener('click', () => {
            if (!deferredPrompt) return;
            // Show the prompt
            deferredPrompt.prompt();
            // Wait for the user to respond to the prompt
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                } else {
                    console.log('User dismissed the install prompt');
                }
                deferredPrompt = null;
                if (installBanner) {
                    installBanner.style.display = 'none';
                }
            });
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            if (installBanner) {
                installBanner.style.display = 'none';
            }
            // Save dismissal state in localStorage
            localStorage.setItem('pwa-banner-dismissed', 'true');
        });
    }

    // Hide banner if app is installed successfully
    window.addEventListener('appinstalled', () => {
        if (installBanner) {
            installBanner.style.display = 'none';
        }
        deferredPrompt = null;
    });
});
