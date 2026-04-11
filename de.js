self.addEventListener('install', (e) => {
  console.log('Service Worker geregistreerd');
});

self.addEventListener('fetch', (e) => {
  // Nodig voor PWA herkenning
});
