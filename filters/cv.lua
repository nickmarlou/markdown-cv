-- Route the Markdown AST into semantic HTML; presentation belongs in CSS.
local function fail(message) error('CV format: ' .. message, 0) end
local function str(value) return pandoc.utils.stringify(value) end
local function key(value) return str(value):lower():match('^%s*(.-)%s*$') end
local function div(blocks, class) return pandoc.Div(blocks, pandoc.Attr('', {class})) end
local function field(value, class)
  return div(value or {}, 'field ' .. (class or ''))
end
local function fields(blocks, allowed)
  local values, rest = {}, pandoc.List()
  for _, block in ipairs(blocks) do
    if block.t == 'DefinitionList' then
      for _, item in ipairs(block.content) do
        local name = key(item[1])
        if not allowed[name] then fail('unexpected field "' .. str(item[1]) .. '"') end
        if values[name] then fail('duplicate field "' .. name .. '"') end
        if #item[2] ~= 1 then fail('field "' .. name .. '" needs one definition') end
        values[name] = item[2][1]
      end
    else rest:insert(block) end
  end
  return values, rest
end
local function split(blocks, level)
  local entries, current = {}, nil
  for _, block in ipairs(blocks) do
    if block.t == 'Header' and block.level == level then
      current = {title=block.content, blocks=pandoc.List()}
      table.insert(entries, current)
    elseif not current then fail('expected a level-' .. level .. ' heading before entry content')
    else current.blocks:insert(block) end
  end
  return entries
end
local function no_headers(blocks, context)
  for _, b in ipairs(blocks) do
    if b.t == 'Header' then fail('unexpected heading in ' .. context) end
  end
end
local function experience(blocks)
  local out = pandoc.List()
  for _, employer in ipairs(split(blocks, 3)) do
    local intro, roles = pandoc.List(), pandoc.List()
    local started = false
    for _, b in ipairs(employer.blocks) do
      if b.t == 'Header' then started = true end
      if started then roles:insert(b) else intro:insert(b) end
    end
    local values, rest = fields(intro, {duration=true})
    if #rest > 0 then fail('employer details must use Duration; put descriptions under a role') end
    local head = pandoc.List({pandoc.Header(3, employer.title)})
    if values.duration then head:insert(field(values.duration, 'duration')) end
    local content = pandoc.List({div(head, 'entry-header')})
    local entries = split(roles, 4)
    if #entries == 0 then fail('each employer needs at least one level-4 role') end
    for _, role in ipairs(entries) do
      local f, body = fields(role.blocks, {dates=true,duration=true,location=true})
      no_headers(body, 'role')
      local header = pandoc.List({pandoc.Header(4, role.title)})
      if f.dates then
        local dates = pandoc.List(f.dates)
        if f.duration then
          local text = str(f.duration)
          local last = dates[#dates]
          if last.t == 'Para' or last.t == 'Plain' then
            last.content:extend({pandoc.Space(),pandoc.Str('(' .. text .. ')')})
          end
        end
        header:insert(field(dates, 'dates'))
      elseif f.duration then header:insert(field(f.duration, 'duration')) end
      if f.location then header:insert(field(f.location, 'location')) end
      local entry = pandoc.List({div(header, 'role-header')})
      entry:extend(body)
      content:insert(div(entry, 'role'))
    end
    out:insert(div(content, 'entry'))
  end
  return out
end
local function education(blocks)
  local out = pandoc.List()
  for _, entry in ipairs(split(blocks, 3)) do
    local f, body = fields(entry.blocks, {degree=true,dates=true,location=true})
    no_headers(body, 'education entry')
    local head = pandoc.List({pandoc.Header(3, entry.title)})
    local detail = pandoc.List()
    if f.degree then detail:extend(f.degree) end
    if f.dates then
      if #detail > 0 and (detail[#detail].t == 'Para' or detail[#detail].t == 'Plain') then
        detail[#detail].content:extend({pandoc.Str(' · (' .. str(f.dates) .. ')')})
      else detail:extend(f.dates) end
    end
    if #detail > 0 then head:insert(field(detail, 'degree')) end
    if f.location then head:insert(field(f.location, 'location')) end
    local content = pandoc.List({div(head, 'entry-header')})
    content:extend(body)
    out:insert(div(content, 'entry'))
  end
  return out
end
function Pandoc(doc)
  local identity = {}
  for _, k in ipairs({'name', 'headline', 'location', 'email', 'linkedin'}) do
    local value = doc.meta[k]
    if value ~= nil then
      local kind = pandoc.utils.type(value)
      if kind ~= 'Inlines' and kind ~= 'string' then
        fail('frontmatter "' .. k .. '" must be a single text value')
      end
      local text = str(value):match('^%s*(.-)%s*$')
      if text ~= '' then identity[k] = text end
    end
  end
  if not identity.name then fail('a nonempty frontmatter "name" is required') end
  local sections, current = {}, nil
  local seen = {}
  for _, b in ipairs(doc.blocks) do
    if b.t == 'Header' and b.level == 1 then
      fail('put your name in YAML frontmatter; start body sections with level-2 headings')
    elseif b.t == 'Header' and b.level == 2 then
      local id = key(b.content)
      if seen[id] then fail('duplicate section "' .. str(b.content) .. '"') end
      seen[id] = true
      current = {title=b.content, id=id, blocks=pandoc.List()}
      table.insert(sections,current)
    elseif current then current.blocks:insert(b)
    else fail('put identity fields in YAML frontmatter; start body sections with level-2 headings') end
  end
  local contact = pandoc.List()
  if identity.email then
    contact:insert(pandoc.Para({pandoc.Link({pandoc.Str(identity.email)}, 'mailto:' .. identity.email)}))
  end
  if identity.linkedin then
    if not identity.linkedin:match('^https?://') then
      fail('frontmatter "linkedin" must be a full http:// or https:// URL')
    end
    local label = identity.linkedin:gsub('^https?://', '')
    contact:insert(pandoc.Para({pandoc.Link({pandoc.Str(label)}, identity.linkedin),
      pandoc.LineBreak(), pandoc.Emph({pandoc.Str('(LinkedIn)')})}))
  end
  if #contact > 0 then
    if seen.contact then
      for _, section in ipairs(sections) do
        if section.id == 'contact' then section.blocks:extend(contact) end
      end
    else
      table.insert(sections, 1, {title={pandoc.Str('Contact')}, id='contact', blocks=contact})
    end
  end
  local sidebar, main = pandoc.List(), pandoc.List()
  local side_names = {contact=true,skills=true,['top skills']=true,languages=true,certifications=true}
  for _, section in ipairs(sections) do
    local content = section.blocks
    if section.id == 'experience' then content = experience(content)
    elseif section.id == 'education' then content = education(content) end
    local blocks = pandoc.List({pandoc.Header(2, section.title)})
    blocks:extend(content)
    local class = section.id == 'summary' and 'summary' or 'cv-section'
    local html = pandoc.List({pandoc.RawBlock('html','<section class="' .. class .. '">')})
    html:extend(blocks)
    html:insert(pandoc.RawBlock('html','</section>'))
    if side_names[section.id] then sidebar:extend(html) else main:extend(html) end
  end
  doc.meta['cv-name'] = pandoc.MetaInlines({pandoc.Str(identity.name)})
  -- Inline template fields must not introduce paragraph margins.
  for _, k in ipairs({'headline','location'}) do
    doc.meta['cv-' .. k] = identity[k] and pandoc.MetaInlines({pandoc.Str(identity[k])}) or nil
  end
  doc.meta['cv-sidebar'] = pandoc.MetaBlocks(sidebar)
  doc.blocks = main
  return doc
end
