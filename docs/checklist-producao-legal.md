# Checklist de producao legal - SEO

## Obrigatorio antes de clientes reais

- [ ] Nomear responsavel interno pelo tratamento de dados.
- [ ] Validar politica de privacidade com jurista.
- [ ] Criar termos de utilizacao e contrato de servico.
- [ ] Criar acordo de tratamento de dados para subcontratantes.
- [ ] Definir prazos de retencao.
- [ ] Definir procedimento de apagamento e exportacao de dados.
- [ ] Ativar HTTPS e HSTS.
- [ ] Configurar `SEO_JWT_SECRET` forte e secreto.
- [ ] Configurar `SEO_ADMIN_EMAIL` e `SEO_ADMIN_PASSWORD` por ambiente.
- [ ] Garantir que `SEO_EXPOSE_DEV_MFA` fica desativado em producao.
- [ ] Encriptar base de dados e backups.
- [ ] Isolar dados por empresa.
- [ ] Implementar recuperacao de conta segura.
- [ ] Rever classes SNC com contabilista certificado.
- [ ] Validar logs e eventos de auditoria.
- [ ] Testar incident response e restauracao de backups.

## Estado do codigo nesta versao

- [x] Autenticacao removida do frontend.
- [x] Credenciais removidas da interface.
- [x] Upload Excel enviado para backend.
- [x] Dependencia `xlsx` removida do frontend.
- [x] Permissoes por perfil implementadas.
- [x] Auditoria pseudonimizada.
- [x] Documentacao RGPD/SNC/IA criada.
- [ ] Persistencia real em PostgreSQL.
- [ ] Gestao real de MFA por email/app autenticadora.
- [ ] Encriptacao de dados em repouso.
- [ ] Multiempresa com isolamento forte.
