
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
# Plate formats
P6    = (2, 3)
P96   = (8, 12)
P384  = (16, 24)
P1536 = (32, 48)
P5600 = (40, 140)

NO_EVENT = 'no event'

class PlateDesign:
   '''Maps plate_ids to plate formats'''
   plates = {}
   @classmethod
   def add_plate(self, plate_id, plate_format):
      '''Add a new plate with the specified format
      '''
      self.plates[plate_id] = plate_format
   
   @classmethod
   def get_plate_format(self, plate_id):
      '''returns the plate_format for a given plate_id
      '''
      return self.plates[plate_id]
   
   @classmethod
   def get_well_ids(self, plate_format):
      '''plate_format - a valid plate format. eg: P96
      '''
      return ['%s%02d'%(ch, num) 
              for ch in alphabet[:plate_format[0]] 
              for num in range(1,plate_format[1]+1)]
   
   @classmethod
   def get_well_id_from_row_col(self, plate_format, (row, col)):
      '''returns a well_id given a plate format and (x,y) (0-indexed) position 
      on a plate
      '''
      import numpy as np
      assert 0 <= row < plate_format[0], 'invalid row %s'%(row)
      assert 0 <= col < plate_format[1], 'invalid col %s'%(col)
      plate = np.array(self.get_well_ids(plate_format)).reshape(plate_format)
      return plate[row,col]
   
   
class Timeline(object):
   '''Represents a timeline.
   '''
   def __init__(self, stock):
      self.stock = stock
      # events : a chronologically ordered list of events
      self.events = []
      # plates : a list of plates included in the experiment
      #         (all events will take place on these plates)
      self.plates = []
      
   def add_event(self, timepoint, action, plate_id, well_ids):
      '''Creates and inserts an event into the timeline.
      '''
      evt = Event(timepoint, action, plate_id, well_ids)
      if len(self.events) == 0:
         self.events = [evt]
      else:
         # search from the end of the list since most insertions will occur there
         for i in range(len(self.events)-1, -1, -1): 
            if evt.get_timepoint() > self.events[i].get_timepoint() or i==0:
               self.events.insert(i+1,evt)
               break
      return evt
   
   def get_event_list(self):
      '''returns a list of events in chronological order
      '''
      # return a copy of the event list
      return list(self.events)
   
   def get_well_ids(self, timepoint=None):
      well_ids = []
      for evt in self.get_event_list():
         if evt.get_timepoint() == timepoint or timepoint == None:
            well_ids += evt.get_well_ids()
      return list(set(well_ids))
   
   def get_event_permutations(self, timepoint):
      '''returns a list of unique permutations of events at a given timepoint.
      Each permutation is a tuple of events that occurred.
      '''
      d = {}
      for event in self.get_events_at_timepoint(timepoint):
         # build a hash, mapping well_ids to lists of events that occurred
         for well in PlateDesign.get_well_ids(PlateDesign.get_plate_format(event.get_plate_id())):
            if well in event.get_well_ids():
               if d.get(well, None) is None:
                  d[well] = [event]
               else:
                  d[well] += [event]
      return set([tuple(set(d[k])) for k in d.keys()])
   
   def get_well_permutations(self, timepoint, plate_format):
      '''returns a list of well-permutations
      Each permutation is a tuple of wells that have a common state.
      d = {(e1,)   :  (A01, A03),
           (e1,e2) :  (A02, B03),
           (e2, )  :  (B02)
           (noop)  :  (B01)... }
      '''
      d = {}
      for well in PlateDesign.get_well_ids(plate_format):
         events_in_well = self.get_events_in_well(well, timepoint)
         if d.get(events_in_well, None) is None:
            d[events_in_well] = [well]
         else:
            d[events_in_well] += [well]
      return set([tuple(set(d[k])) for k in d.keys()])
   
   def get_lineage_tree(self):
      '''Returns a tree that maps the lineage of well states through all timepoints
      '''
      def attach_child_nodes(parent, tp_idx):
         subwells = []
         if len(self.get_unique_timepoints()) <= tp_idx:
            return None
         timepoint = self.get_unique_timepoints()[tp_idx]
         for wells in self.get_well_permutations(timepoint, P6):
            wellset = sorted(set(parent.get_well_ids()).intersection(wells))
            if len(wellset) > 0:
               subwells += [wellset]
         nodes = []
         for i, wells in enumerate(subwells):
            nodes += [LineageNode(parent, 
                                  id = '%s:%s'%(parent.id, i),
                                  wells = wells,
                                  timepoint = timepoint)]
            parent.add_child(nodes[-1])
         return nodes
      
      def build_tree(parent, tp_idx):
         if attach_child_nodes(parent, tp_idx+1) is not None:
            for child in parent.get_children():
               build_tree(child, tp_idx+1)
         return parent
      
      root = LineageNode(None, self.stock, self.get_well_ids(),
                         self.get_unique_timepoints()[0])
      tree = build_tree(root, 0)
      
      return tree
   
   
   def get_unique_timepoints(self):
      '''returns an ascending ordered list of UNIQUE timepoints on this timeline
      '''
      return sorted(set([e.get_timepoint() for e in self.events]))
   
   def get_events_at_timepoint(self, timepoint):
      '''returns each event that occurred at the exact timepoint specified
      '''
      return [evn for evn in self.events if (evn.get_timepoint() == timepoint)]
   
   def get_events_in_well(self, well, timepoint):
      '''returns a tuple of events that occurred in the given well at timepoint
      '''
      return tuple([evt for evt in self.get_events_at_timepoint(timepoint) if well in evt.get_well_ids()])
         
   def save(self, filename):
      '''Saves the timeline to filename
      '''
      raise NotImplemented
   
   def load(self, filename):
      '''Loads a timeline from filename
      '''
      raise NotImplemented
   

class Event(object):
   '''An Event is an action that was taken at some timepoint that is associated
   with a list of well_ids.
   '''
   def __init__(self, timepoint, action, plate_id, well_ids):
      '''timepoint : the timepoint that this event occurred at
      action : the action that took place
      plate_id : plate id
      wells_ids : the list of well_ids that this event effects
      '''
      self.action = action
      self.plate = plate_id
      self.wells = well_ids
      self.timepoint = timepoint

   def get_timepoint(self):
      return self.timepoint
   
   def get_plate_id(self):
      return self.plate
   
   def get_well_ids(self):
      return self.wells
   
   def get_action(self):
      return self.action
   
   def __str__(self):
      return '%s event'%(self.action)

   
class LineageNode(object):
   '''
   '''
   def __init__(self, parent, id, wells, timepoint):
      self.parent = parent
      self.id = id
      self.wells = wells
      self.timepoint = timepoint
      self.children = []
      print str(self)
   
   def get_parent(self):
      return self.parent
   
   def get_children(self):
      return self.children
   
   def get_well_ids(self):
      return self.wells
   
   def add_child(self, childnode):
      self.children += [childnode]
      
   def __str__(self):
      if self.parent:
         return 'p:%s; id:%s; wells:%s'%(self.parent.id, self.id, sorted(self.wells))
      else:
         return 'ROOT; id:%s; wells:%s'%(self.id, sorted(self.wells))


##def build_lineage_tree(timeline):
##   nodelist = []
##   for timepoint in reversed(timeline.get_unique_timepoints()):
##      for i, wells in enumerate(t.get_well_permutations(timepoint, P6)):
##         node = LineageNode(None, id = None,
##                            events = None,
##                            wells = wells,
##                            timepoint = timepoint)
##   parent = None
##   for i, node in enumerate(reversed(nodelist)):
##      while nodelist[j].timepoint :
##         node.parent = parent
##         node.id = str(i)
##      parent = node
##      
##def build_lineage_tree(t, parent_node=None, timepoint_index=0):
##   '''t - timeline
##   '''
##   if timepoint_index >= len(t.get_unique_timepoints()):
##      return 
##   
##   tp = t.get_unique_timepoints()[timepoint_index]
##   if parent_node is None:
##      parent_node = LineageNode(None, ','.join(sorted(t.get_well_ids())), None, t.get_well_ids())
##      
##   for i, events in enumerate(t.get_event_permutations(tp)):
##      # Calculate the subset of wells associated with this node
##      wells = set(parent_node.get_well_ids())
##      for event in events:
##         wells.intersection_update(event.get_well_ids())
##      
##      node = LineageNode(parent_node,
##                         id = '%s : %s'%(parent_node.id, (','.join(sorted(wells)) or 'empty')),
##                         events = events,
##                         wells = wells)
##      parent_node.add_child(node)
##      build_lineage_tree(t, node, timepoint_index+1)
##      
##   return parent_node



#
# Test code here
#
if __name__ == '__main__':
   t = Timeline('U2OS')
   
   PlateDesign.add_plate('fred', P6)
   all_wells = PlateDesign.get_well_ids(PlateDesign.get_plate_format('fred'))
   
   t.add_event(1, 'seed', 'fred', all_wells)
   
   t.add_event(2, 'treatment1', 'fred', ['A01', 'A02', 'A03', 
                                                       'B03'])
   t.add_event(2, 'treatment2', 'fred', [       'A02', 
                                                'B02', 'B03'])
   untreated_wells = set(all_wells) - set(t.get_well_ids(2))
   t.add_event(2, NO_EVENT,     'fred', untreated_wells)

   t.add_event(3, 'treat', 'fred', ['A02'])
   t.add_event(3, 'wash', 'fred', ['A01'])
   untreated_wells = set(all_wells) - set(t.get_well_ids(3))
   t.add_event(3, NO_EVENT, 'fred', untreated_wells)
   t.add_event(4, 'imaging', 'fred', PlateDesign.get_well_ids(P6))

   for p in t.get_well_permutations(2, P6 ):
      print [str(x) for x in p]

##   for p in t.get_event_permutations(2):
##      print [str(x) for x in p]
##
##   for p in t.get_event_permutations(3):
##      print [str(x) for x in p]

   tree = t.get_lineage_tree()
   
   import wx
   app = wx.PySimpleApp()
   f = wx.Frame(None)
   tc = wx.TreeCtrl(f)
   tcroot = tc.AddRoot("ROOT")
   def populate_wx_tree(wxparent, tnode):
      for child in tnode.children:
         subtree = tc.AppendItem(wxparent, ', '.join(child.get_well_ids()))
         populate_wx_tree(subtree, child)
         tc.Expand(subtree)
   populate_wx_tree(tcroot, tree)    
   tc.Expand(tcroot)
   
   f.Show()
   app.MainLoop()
      