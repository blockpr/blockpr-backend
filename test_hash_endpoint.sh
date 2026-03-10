#!/bin/bash

# Script para probar el endpoint de hash con Solana
# Asegúrate de tener las variables de entorno configuradas:
# - HELIUS_API_KEY
# - SOLANA_PRIVATE_KEY
# - DEFAULT_TEST_USER_ID (opcional, para usar un user_id específico)

# Configuración
BASE_URL="http://localhost:5050"
PDF_FILE="test_documents/certificado_prueba_1.pdf"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Test del Endpoint de Hash con Solana ===${NC}\n"
echo -e "${GREEN}Nota: El endpoint ahora NO requiere autenticación${NC}\n"

echo -e "${GREEN}Probando el endpoint de hash con Solana:${NC}"
echo ""

# Comando curl completo (sin token)
curl -X POST "http://localhost:5050/certificates/hash" \
  -F "pdf=@test_documents/certificado_prueba_1.pdf" \
  -F "external_id=test_001" \
  -F "certificate_type=test" \
  -v

echo ""
echo -e "${GREEN}✓ Test completado${NC}"
