import React, { useState } from 'react';

const WorkflowTemplates = ({ templates, onLoadTemplate }) => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const categories = [
    { id: 'all', label: 'All Templates', icon: 'fa-th' },
    { id: 'video', label: 'Video Creation', icon: 'fa-video' },
    { id: 'social', label: 'Social Media', icon: 'fa-share-alt' },
    { id: 'analytics', label: 'Analytics', icon: 'fa-chart-bar' },
    { id: 'automation', label: 'Automation', icon: 'fa-robot' }
  ];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' ||
                           (selectedCategory === 'video' && template.name.toLowerCase().includes('video')) ||
                           (selectedCategory === 'social' && template.name.toLowerCase().includes('social')) ||
                           (selectedCategory === 'analytics' && template.name.toLowerCase().includes('analytics')) ||
                           (selectedCategory === 'automation' && template.name.toLowerCase().includes('optimization'));
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="workflow-templates">
      <div className="templates-header">
        <div className="templates-title">
          <h3>
            <i className="fas fa-template-icon"></i>
            Workflow Templates
          </h3>
          <p>Start with pre-built workflows or create your own</p>
        </div>

        <div className="templates-search">
          <div className="search-input-wrapper">
            <i className="fas fa-search"></i>
            <input
              type="text"
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="templates-categories">
        {categories.map(category => (
          <button
            key={category.id}
            className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(category.id)}
          >
            <i className={`fas ${category.icon}`}></i>
            <span>{category.label}</span>
          </button>
        ))}
      </div>

      <div className="templates-grid">
        {filteredTemplates.map(template => (
          <div key={template.id} className="template-card">
            <div className="template-header">
              <div className="template-icon">
                <i className={`fas ${template.icon}`}></i>
              </div>
              <div className="template-meta">
                <span className="template-nodes">
                  <i className="fas fa-project-diagram"></i>
                  {template.nodes?.length || 0} nodes
                </span>
                <span className="template-connections">
                  <i className="fas fa-link"></i>
                  {template.connections?.length || 0} connections
                </span>
              </div>
            </div>

            <div className="template-content">
              <h4 className="template-name">{template.name}</h4>
              <p className="template-description">{template.description}</p>

              <div className="template-features">
                {template.nodes?.slice(0, 3).map((node, index) => (
                  <span key={index} className="feature-tag">
                    <i className={`fas ${node.icon}`}></i>
                    {node.title}
                  </span>
                ))}
                {template.nodes?.length > 3 && (
                  <span className="feature-tag more">
                    +{template.nodes.length - 3} more
                  </span>
                )}
              </div>
            </div>

            <div className="template-actions">
              <button
                className="btn-preview"
                onClick={() => {/* Preview functionality */}}
              >
                <i className="fas fa-eye"></i>
                Preview
              </button>
              <button
                className="btn-load"
                onClick={() => onLoadTemplate(template)}
              >
                <i className="fas fa-download"></i>
                Load Template
              </button>
            </div>

            {/* Mini Preview */}
            <div className="template-preview">
              <div className="preview-canvas">
                {template.nodes?.slice(0, 5).map((node, index) => (
                  <div
                    key={node.id}
                    className={`preview-node ${node.type}`}
                    style={{
                      left: `${20 + (index * 15)}%`,
                      top: `${30 + (Math.sin(index) * 20)}%`
                    }}
                  >
                    <i className={`fas ${node.icon}`}></i>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="no-templates">
          <div className="no-templates-icon">
            <i className="fas fa-search"></i>
          </div>
          <h4>No templates found</h4>
          <p>Try adjusting your search or category filter</p>
        </div>
      )}

      <div className="templates-footer">
        <button className="btn-create-blank">
          <i className="fas fa-plus"></i>
          Create Blank Workflow
        </button>
      </div>
    </div>
  );
};

export default WorkflowTemplates;