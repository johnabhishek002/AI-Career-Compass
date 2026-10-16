import { useEffect, useState } from 'react'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpenCheck,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  CircleHelp,
  Compass,
  Cpu,
  GraduationCap,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  Sparkles,
  Target,
  Workflow,
} from 'lucide-react'

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const emptyProfile = { name: '', education: '', interests: '', skills: '', career_goal: '' }

async function request(path, options = {}) {
  const response = await fetch(`${apiBase}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map((issue) => issue.msg).join(' ')
      : data.detail || `Request failed (${response.status}).`
    throw new Error(message)
  }
  return data
}

function commaList(value) {
  return value.split(',').map((part) => part.trim()).filter(Boolean)
}

function App() {
  const [profile, setProfile] = useState(emptyProfile)
  const [profileId, setProfileId] = useState(null)
  const [careers, setCareers] = useState([])
  const [activeCareer, setActiveCareer] = useState(null)
  const [health, setHealth] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loadingDashboard, setLoadingDashboard] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadDashboard() {
    setLoadingDashboard(true)
    try {
      const [status, dashboard] = await Promise.all([request('/health'), request('/dashboard')])
      setHealth(status.ollama)
      if (dashboard.profile) {
        setProfileId(dashboard.profile.id)
        setProfile({
          name: dashboard.profile.name,
          education: dashboard.profile.education,
          interests: dashboard.profile.interests.join(', '),
          skills: dashboard.profile.skills.join(', '),
          career_goal: dashboard.profile.career_goal,
        })
        const [matches, saved] = await Promise.all([
          request(`/recommendations/${dashboard.profile.id}`),
          request(`/roadmaps?profile_id=${dashboard.profile.id}`),
        ])
        const savedByCareer = new Map(saved.roadmaps.map((roadmap) => [roadmap.career_id, roadmap]))
        const hydrated = matches.careers.map((career) => {
          const roadmap = savedByCareer.get(career.career_id)
          return { ...career, ...(roadmap || {}), roadmap_id: roadmap?.id, source: roadmap?.source }
        })
        setCareers(hydrated)
        setActiveCareer((current) => hydrated.find((career) => career.career_id === current) ? current : hydrated[0]?.career_id || null)
      }
    } catch (loadError) {
      setError(`Could not load the local dashboard. ${loadError.message}`)
    } finally {
      setLoadingDashboard(false)
    }
  }

  useEffect(() => { loadDashboard() }, [])

  function editProfile(event) {
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submitProfile(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const savedProfile = await request('/profiles', {
        method: 'POST',
        body: JSON.stringify({
          name: profile.name,
          education: profile.education,
          interests: commaList(profile.interests),
          skills: commaList(profile.skills),
          career_goal: profile.career_goal,
        }),
      })
      setProfileId(savedProfile.id)
      const result = await request('/recommendations', {
        method: 'POST',
        body: JSON.stringify({ profile_id: savedProfile.id, limit: 3 }),
      })
      setCareers(result.careers)
      setActiveCareer(result.careers[0]?.career_id || null)
      setNotice(result.notice || '')
      document.getElementById('recommendations')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setBusy(false)
    }
  }

  async function updateTask(roadmap, weekNumber, taskIndex, completed) {
    setError('')
    try {
      const result = await request('/progress', {
        method: 'PATCH',
        body: JSON.stringify({ roadmap_id: roadmap.roadmap_id ?? roadmap.id, week_number: weekNumber, task_index: taskIndex, completed }),
      })
      setCareers((current) => current.map((career) => career.career_id === roadmap.career_id ? { ...career, ...result.roadmap, roadmap_id: result.roadmap.id } : career))
    } catch (progressError) {
      setError(progressError.message)
    }
  }

  const selected = careers.find((career) => career.career_id === activeCareer)
  const completedCount = careers.reduce((total, career) => total + Object.values(career.progress || {}).filter(Boolean).length, 0)
  const taskCount = careers.reduce((total, career) => total + (career.weeks || []).reduce((weekTotal, week) => weekTotal + week.tasks.length, 0), 0)
  const overallProgress = taskCount ? Math.round((completedCount / taskCount) * 100) : 0

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <a className="brand" href="#home" aria-label="Career Compass dashboard">
          <span className="brand-symbol"><Compass size={19} /></span>
          <span>career<span>compass</span></span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="nav-item selected" href="#home"><Activity size={17} /> Overview</a>
          <a className="nav-item" href="#recommendations"><Target size={17} /> Career paths</a>
          <a className="nav-item" href="#roadmap"><BookOpenCheck size={17} /> Learning plan</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card"><LockKeyhole size={16} /><div><strong>Private by design</strong><span>Your data stays on this device.</span></div></div>
          <div className="sidebar-version">AI CAREER COMPASS <span>LOCAL EDITION</span></div>
        </div>
      </aside>

      <div className="main-column" id="home">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div>
          <div className="topbar-right">
            <span className={`model-indicator ${health?.available ? 'online' : ''}`}><span />
              {health?.available ? `Ollama · ${health.model}` : 'Ollama unavailable'}
            </span>
            <span className="avatar" aria-label="Student profile">{profile.name ? profile.name.trim().charAt(0).toUpperCase() : 'S'}</span>
          </div>
        </header>

        <main className="content-area">
          <section className="welcome-banner">
            <div className="banner-orbit orbit-one" /><div className="banner-orbit orbit-two" />
            <div className="banner-content">
              <div className="banner-kicker"><span /> A CLEARER WAY FORWARD</div>
              <h1>{profile.name ? `Welcome back, ${profile.name}.` : 'Your next move starts here.'}</h1>
              <p>Find a direction that fits. Build the skills to go there.</p>
              <a href="#profile" className="banner-link">Explore your profile <ArrowRight size={15} /></a>
            </div>
            <div className="banner-art" aria-hidden="true"><div className="art-ring ring-large" /><div className="art-ring ring-small" /><div className="art-center"><Compass size={38} strokeWidth={1.2} /></div><span className="art-star star-a">✳</span><span className="art-star star-b">✦</span></div>
          </section>

          <section className="metric-grid" aria-label="Learning progress summary">
            <article className="metric-card"><div className="metric-top"><span>CAREER PATHS</span><span className="metric-icon violet"><BriefcaseBusiness size={16} /></span></div><strong>{careers.length || '—'}</strong><span className="metric-caption">matched to your profile</span></article>
            <article className="metric-card"><div className="metric-top"><span>TASKS COMPLETE</span><span className="metric-icon cyan"><BadgeCheck size={16} /></span></div><strong>{taskCount ? `${completedCount}/${taskCount}` : '—'}</strong><span className="metric-caption">across saved roadmaps</span></article>
            <article className="metric-card progress-metric"><div className="metric-top"><span>OVERALL PROGRESS</span><span className="metric-icon blue"><Workflow size={16} /></span></div><strong>{taskCount ? `${overallProgress}%` : '—'}</strong><div className="metric-progress"><span style={{ width: `${overallProgress}%` }} /></div></article>
            <article className="metric-card"><div className="metric-top"><span>GUIDANCE MODE</span><span className="metric-icon green"><Cpu size={16} /></span></div><strong className="mode-value">{careers.length ? (selected?.source === 'ollama' ? 'Local AI' : 'Demo') : 'Ready'}</strong><span className="metric-caption">{health?.available ? health.model : 'No cloud API keys'}</span></article>
          </section>

          {error && <div className="alert error-alert" role="alert"><CircleHelp size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss message">×</button></div>}

          <div className="section-heading" id="profile">
            <div><div className="section-eyebrow">01 / YOUR FOUNDATION</div><h2>Start with what makes you, you.</h2><p>A little context helps build a more useful direction.</p></div>
            {profileId && <button className="quiet-button" onClick={() => { setProfile(emptyProfile); setProfileId(null); setCareers([]); setActiveCareer(null); setNotice('') }}><RefreshCw size={14} /> New profile</button>}
          </div>

          <section className="profile-layout">
            <form className="profile-panel" onSubmit={submitProfile}>
              <div className="panel-heading"><div className="panel-icon"><GraduationCap size={18} /></div><div><h3>Student profile</h3><p>Your information remains local.</p></div><span className="required-note">* REQUIRED</span></div>
              <div className="form-grid">
                <label className="input-wrap">Name <span>OPTIONAL</span><input name="name" value={profile.name} onChange={editProfile} placeholder="First name" maxLength={80} /></label>
                <label className="input-wrap">Education <span>*</span><input name="education" value={profile.education} onChange={editProfile} placeholder="e.g. BSc Computer Science, year 2" minLength={2} maxLength={240} required /></label>
                <label className="input-wrap">Interests <span>* · COMMA SEPARATED</span><input name="interests" value={profile.interests} onChange={editProfile} placeholder="e.g. clean energy, design, research" required /></label>
                <label className="input-wrap">Current skills <span>COMMA SEPARATED</span><input name="skills" value={profile.skills} onChange={editProfile} placeholder="e.g. Python, teamwork, writing" /></label>
                <label className="input-wrap full-width">Career goal <span>*</span><textarea name="career_goal" value={profile.career_goal} onChange={editProfile} placeholder="What would you like to learn, build, or contribute?" rows={3} minLength={2} maxLength={600} required /></label>
              </div>
              <div className="form-actions"><span><LockKeyhole size={13} /> Stored locally in SQLite</span><button className="primary-button" disabled={busy}>{busy ? <><LoaderCircle size={16} className="spin" /> Building your map...</> : <>Find my career paths <ArrowRight size={16} /></>}</button></div>
            </form>
            <aside className="profile-aside">
              <div className="aside-step"><span>1</span><div><strong>Tell us what matters</strong><p>Education, interests, skills, and a goal.</p></div></div>
              <div className="aside-step"><span>2</span><div><strong>Compare your options</strong><p>Transparent matches from a curated skills dataset.</p></div></div>
              <div className="aside-step"><span>3</span><div><strong>Build toward one</strong><p>Get a practical, trackable eight-week plan.</p></div></div>
              <div className="aside-note"><Sparkles size={15} /><span>Local AI is optional. If Ollama is offline, clearly labeled demo guidance keeps the app usable.</span></div>
            </aside>
          </section>

          {loadingDashboard && <div className="loading-row"><LoaderCircle className="spin" size={18} /> Loading saved progress...</div>}
          {notice && <div className="alert demo-alert"><Sparkles size={16} /><span>{notice}</span></div>}

          <section className="recommendation-section" id="recommendations">
            <div className="section-heading results-title">
              <div><div className="section-eyebrow">02 / YOUR CAREER MAP</div><h2>Paths worth exploring.</h2><p>Compare your strongest matches and the skills each path asks for.</p></div>
              {careers.length > 0 && <span className="dataset-pill"><span /> CURATED DATASET MATCH</span>}
            </div>

            {!careers.length && !loadingDashboard ? <div className="empty-state"><span className="empty-icon"><Compass size={25} /></span><h3>Your options will appear here.</h3><p>Complete your profile above to see career matches based on your interests and skills.</p><a href="#profile">Create your profile <ArrowRight size={14} /></a></div> : careers.length > 0 && <>
              <div className="comparison-panel">
                <div className="comparison-head"><div><h3>Career fit comparison</h3><p>Scores reflect skills (60%), interests (30%), and goal keywords (up to 10%).</p></div><span className="comparison-legend"><i /> MATCH SCORE</span></div>
                <div className="comparison-chart" role="img" aria-label="Career match score comparison">
                  {careers.map((career) => <button className={`chart-row ${activeCareer === career.career_id ? 'chart-active' : ''}`} key={career.career_id} onClick={() => setActiveCareer(career.career_id)}>
                    <span className="chart-label">{career.title}</span><span className="chart-track"><span style={{ width: `${career.score}%` }} /></span><strong>{career.score}</strong>
                  </button>)}
                </div>
              </div>

              <div className="career-grid">
                {careers.map((career, index) => <button className={`career-card ${activeCareer === career.career_id ? 'card-active' : ''}`} key={career.career_id} onClick={() => setActiveCareer(career.career_id)}>
                  <div className="career-card-top"><span className="career-rank">0{index + 1}</span><span className="score-badge">{career.score}% FIT</span></div>
                  <h3>{career.title}</h3><p>{career.description}</p>
                  <div className="card-match"><span className="match-symbol"><Check size={13} /></span>{career.matched_interests.length ? career.matched_interests.slice(0, 2).join(' · ') : 'Exploration match'}{career.matched_skills.length > 0 && <span> + {career.matched_skills.length} skill{career.matched_skills.length === 1 ? '' : 's'}</span>}</div>
                  <span className="card-action">View skill gaps <ArrowUpRight size={14} /></span>
                </button>)}
              </div>

              {selected && <section className="detail-section" aria-label={`${selected.title} detail`}>
                <div className="detail-heading"><div><div className="section-eyebrow">03 / SKILL GAP ANALYSIS</div><h2>{selected.title}<ChevronDown size={20} /></h2><p>{selected.fit_explanation || selected.explanation}</p></div><span className={`source-pill ${selected.source === 'ollama' ? 'source-ai' : 'source-demo'}`}>{selected.source === 'ollama' ? <><Sparkles size={12} /> OLLAMA GUIDANCE</> : selected.source === 'demo' ? <><Workflow size={12} /> DEMO GUIDANCE</> : <><Target size={12} /> RULE-BASED MATCH</>}</span></div>
                <div className="gap-grid">
                  <article className="gap-panel have-panel"><div className="gap-head"><span className="gap-icon have-icon"><Check size={16} /></span><div><h3>Skills you bring</h3><p>Already in your profile</p></div><strong>{selected.matched_skills.length}</strong></div>
                    {selected.matched_skills.length ? <div className="skill-list">{selected.matched_skills.map((skill) => <span className="skill-chip present" key={skill}>{skill}</span>)}</div> : <p className="muted-note">No matching skills listed yet. This is a starting point, not a blocker.</p>}
                  </article>
                  <article className="gap-panel grow-panel"><div className="gap-head"><span className="gap-icon grow-icon"><Target size={16} /></span><div><h3>Skills to grow</h3><p>From the curated {selected.title} profile</p></div><strong>{selected.missing_skills.length}</strong></div>
                    {selected.missing_skills.length ? <div className="skill-list">{selected.missing_skills.map((skill) => <span className="skill-chip needed" key={skill}>{skill}</span>)}</div> : <p className="muted-note">All skills in the starter profile are listed in your skills.</p>}
                    <p className="gap-explanation">{selected.guidance_gap_explanation || selected.gap_explanation}</p>
                  </article>
                </div>
              </section>}

              {selected && <section className="roadmap-section" id="roadmap">
                <div className="roadmap-title-row"><div><div className="section-eyebrow">04 / YOUR LEARNING PLAN</div><h2>Eight weeks to explore {selected.title}.</h2><p>Small, practical steps. Check off each task as you complete it.</p></div><div className="roadmap-progress"><span>{Object.values(selected.progress || {}).filter(Boolean).length}<small> / {selected.weeks?.reduce((count, week) => count + week.tasks.length, 0) || 0}</small></span><div><strong>TASKS DONE</strong><div className="roadmap-progress-track"><i style={{ width: `${selected.weeks?.flatMap((week) => week.tasks).length ? (Object.values(selected.progress || {}).filter(Boolean).length / selected.weeks.flatMap((week) => week.tasks).length) * 100 : 0}%` }} /></div></div></div></div>
                {!selected.roadmap_id ? <div className="empty-roadmap"><BookOpenCheck size={20} /><span>No saved roadmap for this career yet.</span><button onClick={async () => {
                  setBusy(true)
                  try {
                    const roadmap = await request('/roadmaps', { method: 'POST', body: JSON.stringify({ profile_id: profileId, career_id: selected.career_id }) })
                    setCareers((current) => current.map((career) => career.career_id === roadmap.career_id ? { ...career, ...roadmap, roadmap_id: roadmap.id } : career))
                    setNotice(roadmap.notice || '')
                  } catch (roadmapError) { setError(roadmapError.message) } finally { setBusy(false) }
                }} disabled={busy}>{busy ? 'Generating...' : 'Generate roadmap'} <ArrowRight size={14} /></button></div> : <div className="roadmap-list">
                  {selected.weeks?.map((week) => <article className="week-card" key={week.week}>
                    <div className="week-side"><span>WEEK</span><strong>{String(week.week).padStart(2, '0')}</strong><span className="week-connector" /></div>
                    <div className="week-main"><div className="week-title-line"><h3>{week.title}</h3><span className="week-count">{week.tasks.filter((_, index) => selected.progress?.[`${week.week}:${index}`]).length}/{week.tasks.length} DONE</span></div>
                      <div className="task-list">{week.tasks.map((task, index) => {
                        const id = `task-${selected.roadmap_id}-${week.week}-${index}`
                        const checked = Boolean(selected.progress?.[`${week.week}:${index}`])
                        return <label className={`task-item ${checked ? 'task-done' : ''}`} htmlFor={id} key={id}><input id={id} type="checkbox" checked={checked} onChange={(event) => updateTask(selected, week.week, index, event.target.checked)} /><span className="custom-check"><Check size={12} /></span><span>{task}</span></label>
                      })}</div>
                      <div className="project-suggestion"><span><Sparkles size={13} /> PROJECT IDEA</span><p>{week.project_suggestion}</p></div>
                    </div>
                  </article>)}
                </div>}
              </section>}
            </>}
          </section>

          <footer className="page-footer"><span>AI CAREER COMPASS</span><span>LOCAL-FIRST GUIDANCE <i /> YOUR DATA STAYS YOURS</span><a href="https://www.onetonline.org/" target="_blank" rel="noreferrer">Explore occupations <ArrowUpRight size={12} /></a></footer>
        </main>
      </div>
    </div>
  )
}

export default App