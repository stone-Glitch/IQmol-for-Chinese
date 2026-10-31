/*******************************************************************************
         
  Copyright (C) 2022 Andrew Gilbert
      
  This file is part of IQmol, a free molecular visualization program. See
  <http://iqmol.org> for more details.
         
  IQmol is free software: you can redistribute it and/or modify it under the
  terms of the GNU General Public License as published by the Free Software  
  Foundation, either version 3 of the License, or (at your option) any later  
  version.

  IQmol is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
  FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
  details.
      
  You should have received a copy of the GNU General Public License along
  with IQmol.  If not, see <http://www.gnu.org/licenses/>.
   
********************************************************************************/

#include "ExcitedStatesLayer.h"
#include "Configurator/ExcitedStatesConfigurator.h"
#include "Data/ExcitedStates.h"


namespace IQmol {
namespace Layer {


ExcitedStates::ExcitedStates(Data::ExcitedStates const& states) : Base("Excited States"),
   m_excitedStates(states), m_configurator(0)
{
   // [i18n] 初始化列表中的标签为裸字符串，此处覆盖为译文，
   // 使 lupdate 可提取、界面显示中文。
   setText(tr("Excited States"));

}



ExcitedStates::~ExcitedStates()
{
   if (m_configurator) delete m_configurator;
}



void ExcitedStates::configure()
{
   if (!m_configurator) m_configurator = new Configurator::ExcitedStates(*this);
   if (m_configurator) m_configurator->display();
}

} } // end namespace IQmol::Layer
