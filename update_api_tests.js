const fs = require('fs');
const filePath = 'frontend/src/lib/__tests__/api.test.ts';
let content = fs.readFileSync(filePath, 'utf8');

const newTests = `

  describe('auth endpoints', () => {
    it('githubLogin', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.auth.githubLogin();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/github', expect.objectContaining({ method: 'GET' }));
    });

    it('githubCallback', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.auth.githubCallback('code1', 'state1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/callback?code=code1&state=state1', expect.objectContaining({ method: 'GET' }));
    });

    it('register', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.auth.register({ email: 'a@a.com', password: '123' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/register', expect.objectContaining({ method: 'POST', body: JSON.stringify({ email: 'a@a.com', password: '123' }) }));
    });
  });

  describe('boards endpoints', () => {
    it('list', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.boards.list();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/boards', expect.objectContaining({ method: 'GET' }));
    });

    it('create', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.boards.create({ name: 'board1' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/boards', expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'board1' }) }));
    });

    it('get', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.boards.get('b1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/boards/b1', expect.objectContaining({ method: 'GET' }));
    });

    it('update', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.boards.update('b1', { name: 'board2' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/boards/b1', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ name: 'board2' }) }));
    });

    it('delete', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.boards.delete('b1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/boards/b1', expect.objectContaining({ method: 'DELETE' }));
    });
  });

  describe('agents endpoints', () => {
    it('list', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.agents.list();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents', expect.objectContaining({ method: 'GET' }));
      await api.agents.list('b1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents?board_id=b1', expect.objectContaining({ method: 'GET' }));
    });

    it('create', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.agents.create({ name: 'a1', system_prompt: 'p' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents', expect.objectContaining({ method: 'POST' }));
    });

    it('get', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.agents.get('a1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents/a1', expect.objectContaining({ method: 'GET' }));
    });

    it('update', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.agents.update('a1', { name: 'a2' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents/a1', expect.objectContaining({ method: 'PUT' }));
    });

    it('delete', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.agents.delete('a1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/agents/a1', expect.objectContaining({ method: 'DELETE' }));
    });
  });

  describe('teams endpoints', () => {
    it('list', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.teams.list();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams', expect.objectContaining({ method: 'GET' }));
      await api.teams.list('b1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams?board_id=b1', expect.objectContaining({ method: 'GET' }));
    });

    it('create', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.teams.create({ name: 't1' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams', expect.objectContaining({ method: 'POST' }));
    });

    it('get', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.teams.get('t1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams/t1', expect.objectContaining({ method: 'GET' }));
    });

    it('update', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.teams.update('t1', { name: 't2' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams/t1', expect.objectContaining({ method: 'PUT' }));
    });

    it('delete', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.teams.delete('t1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/teams/t1', expect.objectContaining({ method: 'DELETE' }));
    });
  });

  describe('generations endpoints', () => {
    it('list', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.generations.list('b1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/generations?board_id=b1', expect.objectContaining({ method: 'GET' }));
    });

    it('get', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.generations.get('g1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/generations/g1', expect.objectContaining({ method: 'GET' }));
    });

    it('delete', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.generations.delete('g1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/generations/g1', expect.objectContaining({ method: 'DELETE' }));
    });
  });

  describe('billing endpoints', () => {
    it('status', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.billing.status();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/billing/status', expect.objectContaining({ method: 'GET' }));
    });

    it('createSubscriptionCheckout', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.billing.createSubscriptionCheckout('pro', 'monthly');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/billing/checkout', expect.objectContaining({ method: 'POST', body: JSON.stringify({ type: 'subscription', tier: 'pro', billing_period: 'monthly' }) }));
    });

    it('createPackCheckout', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.billing.createPackCheckout('large');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/billing/checkout', expect.objectContaining({ method: 'POST', body: JSON.stringify({ type: 'pack', pack_size: 'large' }) }));
    });

    it('portal', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.billing.portal();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/billing/portal', expect.objectContaining({ method: 'GET' }));
    });
  });

  describe('admin endpoints', () => {
    it('listUsers', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.listUsers();
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users', expect.objectContaining({ method: 'GET' }));

      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.listUsers({ search: 'test', page: 2 });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users?search=test&page=2', expect.objectContaining({ method: 'GET' }));
    });

    it('getUser', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.getUser('u1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users/u1', expect.objectContaining({ method: 'GET' }));
    });

    it('changeTier', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.changeTier('u1', 'pro');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users/u1/tier', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ tier: 'pro' }) }));
    });

    it('grantCredits', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.grantCredits('u1', { pack_credits: 100 });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users/u1/credits', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ pack_credits: 100 }) }));
    });

    it('changeRole', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.changeRole('u1', 'ADMIN');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users/u1/role', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ role: 'ADMIN' }) }));
    });

    it('revokeApiKey', async () => {
      const { api } = await import('../api');
      (global.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await api.admin.revokeApiKey('u1', 'k1');
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/admin/users/u1/api-keys/k1', expect.objectContaining({ method: 'DELETE' }));
    });
  });
`;

content = content.replace('});\n', newTests + '});\n');
fs.writeFileSync(filePath, content);
