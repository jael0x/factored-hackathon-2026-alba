import type { ProductCopy } from "../products";
import type { Role } from "../routes";

const products: ProductCopy = {
  types: {
    "Cuenta Ahorro": { label: "Cuenta de ahorro", gender: "feminine" },
    "Cuenta Corriente": { label: "Cuenta corriente", gender: "feminine" },
    "Tarjeta Crédito": { label: "Tarjeta de crédito", gender: "feminine" },
    "Tarjeta Débito": { label: "Tarjeta de débito", gender: "feminine" },
    "Préstamo Personal": { label: "Préstamo personal", gender: "masculine" },
    "Préstamo Hipotecario": { label: "Préstamo hipotecario", gender: "masculine" },
    Inversión: { label: "Inversión", gender: "feminine" },
    Seguro: { label: "Seguro", gender: "masculine" },
  },
  statuses: {
    Active: { feminine: "Activa", masculine: "Activo" },
    Blocked: { feminine: "Bloqueada", masculine: "Bloqueado" },
    Suspended: { feminine: "Suspendida", masculine: "Suspendido" },
  },
  maskedEnding: { feminine: "terminada en", masculine: "terminado en" },
  askAbout: { credit_card: "Tarjeta de crédito", personal_loan: "Préstamo personal" },
};

const signInWith: Record<Role, string> = {
  customer: "Entra de nuevo con tu documento.",
  consultant: "Entra de nuevo con tu correo y tu código de empleado.",
};

// Spanish sets the keys: pt.ts is typed as Messages, so a missing or extra label fails tsc.
export const es = {
  language: "Idioma",
  signOut: "Salir",
  loading: "Cargando",
  retry: "Reintentar",
  checkConnection: "Revisa tu conexión e inténtalo de nuevo.",
  login: {
    demoConfigFailed: "No pudimos leer la configuración del demo.",
    yourCode: "Tu código",
    sendCode: "Enviar código",
    sending: "Enviando…",
    sendFailed: "No pudimos enviar la solicitud. Inténtalo de nuevo.",
    customer: {
      title: "Entra a tu cuenta",
      lede: "Escribe tu número de documento. Te enviaremos un código de un solo uso al correo registrado.",
      notice:
        "Si tu documento está registrado y tiene un correo asociado, te enviaremos un código. Si no te llega, acércate a una sucursal para registrar tu correo.",
      panelTitle: "Tu documento",
      documentNumber: "Número de documento",
      document: "Documento",
      change: "Cambiar documento",
      otherLogin: "Acceso para asesores",
    },
    consultant: {
      title: "Entra como asesor",
      lede: "Escribe tu correo y tu código de empleado. Te enviaremos un código de un solo uso a ese correo.",
      notice: "Si tus datos corresponden a un asesor activo, te enviaremos un código.",
      panelTitle: "Tus datos",
      email: "Correo",
      employeeCode: "Código de empleado",
      change: "Cambiar datos",
      otherLogin: "Acceso para clientes",
    },
  },
  code: {
    label: "Código",
    checkEmail: "Revisa tu correo y escribe el código.",
    resent: "Pedimos otro código. Revisa tu correo.",
    validFor: (minutes: number) => `El código vale ${minutes} minutos.`,
    open: "Abrir sesión",
    resend: "Pedir otro código",
    rejected: "El código no es válido o venció.",
    unreachable: "No pudimos abrir la sesión. Inténtalo de nuevo.",
    resendFailed: "No pudimos pedir otro código. Inténtalo de nuevo.",
  },
  demo: {
    close: "Cerrar",
    pickRandom: "Elegir al azar",
    searching: "Buscando",
    searchFailed: "No pudimos buscar.",
    noMatch: "Nadie coincide con esa búsqueda.",
    results: "Resultados",
    customers: {
      heading: "Usuarios de prueba",
      help: "Solo en el demo. Elegir a alguien llena su documento y cierra este panel; el código igual llega por correo.",
      queryLabel: "Nombre, documento o número de cliente",
      document: "documento",
      endingIn: "terminado en",
    },
    consultants: {
      heading: "Asesores de prueba",
      help: "Solo en el demo. Elegir a alguien llena su correo y su código de empleado y cierra este panel; el código igual llega por correo.",
      queryLabel: "Nombre, código de empleado o número de asesor",
      employeeCode: "código de empleado",
    },
  },
  sessionEnded: {
    title: "Tu sesión terminó",
    lasts: "La sesión dura 15 minutos y no se renueva sola.",
    signInWith,
    again: "Volver a entrar",
  },
  home: {
    greeting: (name: string) => `Hola, ${name}`,
    loadFailed: "No pudimos cargar tus productos.",
    empty: "Todavía no tienes productos con nosotros.",
    askAbout: "Preguntar por",
  },
  consultantHome: {
    loadFailed: "No pudimos cargar tus datos.",
    lede: "Los casos en revisión aparecerán aquí.",
    employee: "empleado",
  },
  products,
};

export type Messages = typeof es;
