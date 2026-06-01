document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('backdrop');
  const navToggles = document.querySelectorAll('.nav-toggle');
  const subNavs = document.querySelectorAll('.sub-nav');
  const navLinks = document.querySelectorAll('.sub-nav a');

  // Open/Close sidebar
  const toggleSidebar = () => {
    sidebar.classList.toggle('open');
    backdrop.classList.toggle('open');
  };

  toggleBtn.addEventListener('click', toggleSidebar);
  backdrop.addEventListener('click', toggleSidebar);

  // Submenu expand/collapse
  navToggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const subNav = btn.nextElementSibling;
      const isOpen = subNav.classList.contains('open');

      // Close all other submenus first (optional)
      subNavs.forEach(s => s.classList.remove('open'));
      navToggles.forEach(b => b.classList.remove('active'));

      if (!isOpen) {
        subNav.classList.add('open');
        btn.classList.add('active');
      }
    });
  });

  // Highlight active page & auto-open its parent
  const currentPage = window.location.pathname.split('/').pop();
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPage || link.href.includes(currentPage)) {
      link.classList.add('active');
      const parentToggle = link.closest('.sub-nav')?.previousElementSibling;
      if (parentToggle) {
        parentToggle.classList.add('active');
        link.closest('.sub-nav').classList.add('open');
      }
    }
  });
});