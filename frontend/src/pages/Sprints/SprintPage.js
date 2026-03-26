import React, { useState, useEffect, useContext, useRef } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { projectAPI, taskAPI } from "../../services/api";
import { getProjectSprints, createSprint, startSprint, completeSprint, deleteSprint, addTaskToSprint } from "../../services/sprintAPI";
import { getBacklogTasks, getAvailableSprintTasks } from "../../services/sprintAPI";
import { AuthContext } from "../../context/AuthContext";
import "./SprintPage.css";
import SprintForm from "../../components/Sprints/SprintForm";
import SprintList from "../../components/Sprints/SprintList";
import BacklogView from "../../components/Sprints/BacklogView";
import Loader from "../../components/Loader/Loader";

const SprintPage = () => {
  const { projectId } = useParams();
  const location = useLocation();
  const { user } = useContext(AuthContext);
  const [project, setProject] = useState(null);
  const [sprints, setSprints] = useState([]);
  const [backlogTasks, setBacklogTasks] = useState([]); // Tasks moved from completed sprints
  const [availableTasks, setAvailableTasks] = useState([]); // Tasks available to add to sprints
  const [sprintTasks, setSprintTasks] = useState({}); // Tasks in each sprint { sprintId: [tasks] }
  const [showSprintForm, setShowSprintForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isOwner, setIsOwner] = useState(false);
  const previousLocationRef = useRef(location.pathname);
  const lastFetchTimeRef = useRef(0);

  useEffect(() => {
    if (projectId && user) {
      fetchProjectData();
    }
  }, [projectId, user?.id]); // Only re-fetch when projectId or user changes

  // Track location changes - refresh when navigating back to this page
  useEffect(() => {
    const currentPath = location.pathname;
    const previousPath = previousLocationRef.current;
    
    // If we're coming back to sprints page from a different page, refresh
    if (previousPath && previousPath !== currentPath && currentPath.includes('/sprints') && projectId && user) {
      console.log('[SprintPage] Navigation detected, refreshing data...');
      const now = Date.now();
      // Debounce: only fetch if it's been more than 300ms since last fetch
      if (now - lastFetchTimeRef.current > 300) {
        fetchProjectData();
        lastFetchTimeRef.current = now;
      }
    }
    
    previousLocationRef.current = currentPath;
  }, [location.pathname, projectId, user]);

  // Refetch data when page becomes visible (user navigates back)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && projectId && user) {
        fetchProjectData();
      }
    };

    const handleFocus = () => {
      if (projectId && user) {
        fetchProjectData();
      }
    };

    // Listen for custom events from other components (like task deletion)
    const handleDataChange = (event) => {
      // Refresh if event is for this project or if no projectId specified (refresh all)
      if (!event.detail || !event.detail.projectId || String(event.detail.projectId) === String(projectId)) {
        console.log('[SprintPage] Received sprintDataChanged event, refreshing...');
        const now = Date.now();
        if (now - lastFetchTimeRef.current > 300) {
          fetchProjectData();
          lastFetchTimeRef.current = now;
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('sprintDataChanged', handleDataChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('sprintDataChanged', handleDataChange);
    };
  }, [projectId, user]);

  const fetchProjectData = async () => {
    try {
      console.log('[SprintPage] Fetching project data...');
      lastFetchTimeRef.current = Date.now();
      setLoading(true);
      setError("");

      // Fetch project and sprints first (required data)
      const [projectData, sprintsData] = await Promise.all([
        projectAPI.getById(projectId),
        getProjectSprints(projectId)
      ]);

      // Set project details
      setProject(projectData.project);
      
      // Check if current user is owner
      const owner = projectData.project.owner_id === user.id || 
                     projectData.project.user_id === user.id ||
                     projectData.project.is_owner === true;
      setIsOwner(owner);

      // Set sprints
      setSprints(sprintsData.sprints || []);

      // Fetch tasks for all sprints at once (optimized)
      const allTasks = await taskAPI.getByProject(projectId);
      const tasksData = allTasks.tasks || [];
      
      // Separate tasks by sprint, backlog, and available
      const tasksBySprint = {};
      const backlog = [];
      const available = [];
      
      tasksData.forEach(task => {
        if (task.sprint_id) {
          // Task is in a sprint
          const sprintId = String(task.sprint_id);
          if (!tasksBySprint[sprintId]) {
            tasksBySprint[sprintId] = [];
          }
          tasksBySprint[sprintId].push(task);
        } else if (task.in_backlog) {
          // Task is in backlog (moved from completed sprint)
          backlog.push(task);
        } else {
          // Task is available for sprint assignment
          available.push(task);
        }
      });
      
      setSprintTasks(tasksBySprint);
      setBacklogTasks(backlog);
      setAvailableTasks(available);
      
      console.log('[SprintPage] Data fetched successfully. Sprint tasks:', Object.keys(tasksBySprint).map(id => `${id}: ${tasksBySprint[id].length} tasks`));

    } catch (err) {
      console.error('[SprintPage] Error fetching data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSprint = async (sprintData) => {
    try {
      setError("");
      await createSprint(projectId, sprintData);
      setShowSprintForm(false);
      
      // Optimized: only fetch updated sprints list
      const sprintsData = await getProjectSprints(projectId);
      setSprints(sprintsData.sprints || []);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleStartSprint = async (sprintId) => {
    try {
      setError("");
      await startSprint(sprintId);
      
      // Optimized: only fetch updated sprints list
      const sprintsData = await getProjectSprints(projectId);
      setSprints(sprintsData.sprints || []);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCompleteSprint = async (sprintId) => {
    if (!window.confirm("Complete this sprint? Incomplete tasks will be moved to backlog.")) {
      return;
    }
    
    try {
      setError("");
      await completeSprint(sprintId);
      
      // Optimized: fetch sprints and tasks (tasks moved to backlog)
      const [sprintsData, tasksData] = await Promise.all([
        getProjectSprints(projectId),
        taskAPI.getByProject(projectId)
      ]);
      
      setSprints(sprintsData.sprints || []);
      
      // Re-categorize tasks
      const tasksBySprint = {};
      const backlog = [];
      const available = [];
      
      tasksData.tasks.forEach(task => {
        if (task.sprint_id) {
          const sid = String(task.sprint_id);
          if (!tasksBySprint[sid]) tasksBySprint[sid] = [];
          tasksBySprint[sid].push(task);
        } else if (task.in_backlog) {
          backlog.push(task);
        } else {
          available.push(task);
        }
      });
      
      setSprintTasks(tasksBySprint);
      setBacklogTasks(backlog);
      setAvailableTasks(available);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteSprint = async (sprintId) => {
    if (!window.confirm("Delete this sprint? All tasks will be moved to backlog.")) {
      return;
    }
    
    try {
      setError("");
      await deleteSprint(sprintId);
      
      // Optimized refresh: only fetch sprints and tasks, not project/members
      const [sprintsData, tasksData] = await Promise.all([
        getProjectSprints(projectId),
        taskAPI.getByProject(projectId)
      ]);
      
      setSprints(sprintsData.sprints || []);
      
      // Re-categorize tasks
      const tasksBySprint = {};
      const backlog = [];
      const available = [];
      
      tasksData.tasks.forEach(task => {
        if (task.sprint_id) {
          const sid = String(task.sprint_id);
          if (!tasksBySprint[sid]) tasksBySprint[sid] = [];
          tasksBySprint[sid].push(task);
        } else if (task.in_backlog) {
          backlog.push(task);
        } else {
          available.push(task);
        }
      });
      
      setSprintTasks(tasksBySprint);
      setBacklogTasks(backlog);
      setAvailableTasks(available);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAddTaskToSprint = async (sprintId, taskId) => {
    try {
      setError("");
      console.log('[SprintPage] Adding task to sprint...');
      await addTaskToSprint(sprintId, taskId);
      
      console.log('[SprintPage] Task added, fetching updated data...');
      // Force immediate refresh of all data to show updated counts and tasks
      await fetchProjectData();
      
      // Dispatch event to notify other components
      window.dispatchEvent(new CustomEvent('sprintDataChanged', { 
        detail: { projectId } 
      }));
      
      console.log('[SprintPage] Data refreshed successfully');
      // Close the task selector dropdown after successful add
      return true;
    } catch (err) {
      console.error('[SprintPage] Failed to add task:', err);
      setError(err.message);
      alert(err.message || "Failed to add task to sprint");
      return false;
    }
  };

  if (loading) {
    return (
      <div className="sprint-page-loading">
        <div style={{ position: 'relative', minHeight: '400px' }}>
          <Loader />
        </div>
      </div>
    );
  }

  if (!project) {
    return <div className="sprint-page-error">Project not found</div>;
  }

  const activeSprint = sprints.find(s => s.status === "active");
  const plannedSprints = sprints.filter(s => s.status === "planned");
  const completedSprints = sprints.filter(s => s.status === "completed");

  return (
    <div className="sprint-page">
      <div className="sprint-page-header">
        <div className="sprint-page-breadcrumb">
          <Link to="/projects" className="breadcrumb-link">Projects</Link>
          <span className="breadcrumb-separator">/</span>
          <Link to={`/projects/${projectId}/tasks`} className="breadcrumb-link">
            {project.name}
          </Link>
          <span className="breadcrumb-separator">/</span>
          <span className="breadcrumb-current">Sprints</span>
        </div>
        
        <h1 className="sprint-page-title">Sprint Management</h1>
        
        {error && <div className="sprint-page-error">{error}</div>}
        
        {isOwner && (
          <button 
            className="create-sprint-btn"
            onClick={() => setShowSprintForm(true)}
            disabled={showSprintForm}
          >
            + Create Sprint
          </button>
        )}
      </div>

      {showSprintForm && (
        <SprintForm
          onSubmit={handleCreateSprint}
          onCancel={() => setShowSprintForm(false)}
        />
      )}

      <div className="sprint-sections">
        {/* Active Sprint */}
        {activeSprint && (
          <div className="sprint-section active-sprint-section">
            <h2 className="section-title">Active Sprint</h2>
            <SprintList
              sprints={[activeSprint]}
              projectId={projectId}
              isOwner={isOwner}
              onStart={handleStartSprint}
              onComplete={handleCompleteSprint}
              onDelete={handleDeleteSprint}
              onRefresh={fetchProjectData}
              onAddTask={handleAddTaskToSprint}
              backlogTasks={backlogTasks}
              availableTasks={availableTasks}
              sprintTasks={sprintTasks}
            />
          </div>
        )}

        {/* Backlog - Only show when there are no active or planned sprints */}
        {!activeSprint && plannedSprints.length === 0 && backlogTasks.length > 0 && (
          <div className="sprint-section backlog-section">
            <h2 className="section-title">
              Backlog <span className="task-count">({backlogTasks.length} tasks)</span>
            </h2>
            <BacklogView
              tasks={backlogTasks}
              projectId={projectId}
              sprints={plannedSprints}
              isOwner={isOwner}
              onRefresh={fetchProjectData}
            />
          </div>
        )}

        {/* Planned Sprints */}
        {plannedSprints.length > 0 && (
          <div className="sprint-section planned-sprints-section">
            <h2 className="section-title">Planned Sprints ({plannedSprints.length})</h2>
            <SprintList
              sprints={plannedSprints}
              projectId={projectId}
              isOwner={isOwner}
              onStart={handleStartSprint}
              onComplete={handleCompleteSprint}
              onAddTask={handleAddTaskToSprint}
              backlogTasks={backlogTasks}
              availableTasks={availableTasks}
              onDelete={handleDeleteSprint}
              onRefresh={fetchProjectData}
              sprintTasks={sprintTasks}
            />
          </div>
        )}

        {/* Completed Sprints */}
        {completedSprints.length > 0 && (
          <div className="sprint-section completed-sprints-section">
            <h2 className="section-title">Completed Sprints ({completedSprints.length})</h2>
            <SprintList
              sprints={completedSprints}
              projectId={projectId}
              isOwner={isOwner}
              onStart={handleStartSprint}
              onComplete={handleCompleteSprint}
              onDelete={handleDeleteSprint}
              onRefresh={fetchProjectData}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default SprintPage;
