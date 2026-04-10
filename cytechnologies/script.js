const iniciarEscenaEntrada = () => {
  const escena = document.getElementById('escena-entrada');

  if (!escena) {
    return;
  }

  const prefiereReducirMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefiereReducirMovimiento) {
    escena.remove();
    return;
  }

  let escenaCerrada = false;

  const cerrarEscena = () => {
    if (escenaCerrada) {
      return;
    }

    escenaCerrada = true;
    escena.classList.add('escena-entrada--oculta');
    document.body.classList.remove('escena-activa');

    window.setTimeout(() => {
      escena.remove();
    }, 760);
  };

  document.body.classList.add('escena-activa');
  window.setTimeout(cerrarEscena, 2200);
  escena.addEventListener('click', cerrarEscena, { once: true });
};

const iniciarAnimacionesEntrada = () => {
  const elementosAnimables = document.querySelectorAll('.animable');

  if (!('IntersectionObserver' in window)) {
    elementosAnimables.forEach((elemento) => {
      elemento.classList.add('visible');
    });
    return;
  }

  const observador = new IntersectionObserver(
    (entradas, observadorLocal) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) {
          return;
        }

        entrada.target.classList.add('visible');
        observadorLocal.unobserve(entrada.target);
      });
    },
    {
      threshold: 0.2,
      rootMargin: '0px 0px -40px 0px',
    }
  );

  elementosAnimables.forEach((elemento, indice) => {
    elemento.style.setProperty('--retardo', `${indice * 120}ms`);
    observador.observe(elemento);
  });
};

const iniciarContadores = () => {
  const elementosContador = document.querySelectorAll('[data-objetivo]');
  const formatoEntero = new Intl.NumberFormat('es-MX');

  const animarContador = (elemento) => {
    const objetivo = Number(elemento.dataset.objetivo || '0');
    const sufijo = elemento.dataset.sufijo || '';
    const inicio = performance.now();
    const duracion = 1400;

    const actualizar = (momento) => {
      const progreso = Math.min((momento - inicio) / duracion, 1);
      const valorActual = Math.round(progreso * objetivo);

      elemento.textContent = `${formatoEntero.format(valorActual)}${sufijo}`;

      if (progreso < 1) {
        requestAnimationFrame(actualizar);
      }
    };

    requestAnimationFrame(actualizar);
  };

  if (!('IntersectionObserver' in window)) {
    elementosContador.forEach(animarContador);
    return;
  }

  const observadorContador = new IntersectionObserver(
    (entradas, observadorLocal) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) {
          return;
        }

        animarContador(entrada.target);
        observadorLocal.unobserve(entrada.target);
      });
    },
    {
      threshold: 0.4,
    }
  );

  elementosContador.forEach((elemento) => {
    observadorContador.observe(elemento);
  });
};

const iniciarEfectoHero = () => {
  const contenedorHero = document.querySelector('.hero');
  const panelVisual = document.querySelector('.hero__visual');

  if (!contenedorHero || !panelVisual) {
    return;
  }

  const activarSoloEnDesktop = () => window.innerWidth >= 980;

  contenedorHero.addEventListener('pointermove', (evento) => {
    if (!activarSoloEnDesktop()) {
      return;
    }

    const rectangulo = contenedorHero.getBoundingClientRect();
    const rectanguloPanel = panelVisual.getBoundingClientRect();
    const posicionLocalX = Math.min(Math.max(evento.clientX - rectanguloPanel.left, 0), rectanguloPanel.width);
    const posicionLocalY = Math.min(Math.max(evento.clientY - rectanguloPanel.top, 0), rectanguloPanel.height);
    const posicionX = posicionLocalX / rectangulo.width;
    const posicionY = posicionLocalY / rectangulo.height;

    const rotacionY = (posicionX - 0.5) * 8;
    const rotacionX = (0.5 - posicionY) * 6;

    panelVisual.style.transform = `perspective(1000px) rotateX(${rotacionX}deg) rotateY(${rotacionY}deg)`;
    panelVisual.style.setProperty('--cursor-x', `${posicionLocalX}px`);
    panelVisual.style.setProperty('--cursor-y', `${posicionLocalY}px`);
  });

  contenedorHero.addEventListener('pointerleave', () => {
    panelVisual.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
    panelVisual.style.setProperty('--cursor-x', '50%');
    panelVisual.style.setProperty('--cursor-y', '50%');
  });
};

const colocarAnioActual = () => {
  const etiquetaAnio = document.getElementById('anio-actual');

  if (etiquetaAnio) {
    etiquetaAnio.textContent = String(new Date().getFullYear());
  }
};

document.addEventListener('DOMContentLoaded', () => {
  iniciarEscenaEntrada();
  iniciarAnimacionesEntrada();
  iniciarContadores();
  iniciarEfectoHero();
  colocarAnioActual();
});
