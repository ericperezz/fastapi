# Uso de la API

## Flujo principal

1. Registrar usuario.
2. Hacer login.
3. Copiar access token.
4. Usar access token en endpoints protegidos.
5. Usar refresh token para renovar sesión.
6. Cerrar sesión con logout.

## Register

```http
POST /api/v1/auth/register